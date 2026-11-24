"""Minimal bounds-checked x64 PE inventory, no execution or binary modification."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct


@dataclass(frozen=True)
class Section:
    name: str
    rva: int
    virtual_size: int
    file_offset: int
    file_size: int
    characteristics: int

    @property
    def executable(self):
        return bool(self.characteristics & 0x20000000)


class PEFormatError(ValueError):
    pass


class PE:
    def __init__(self, path):
        self.path = Path(path)
        # Restrict input to the supplied PE file. Never execute or patch it.
        self.data = self.path.read_bytes()
        b = self.data
        if len(b) < 0x100 or b[:2] != b"MZ":
            raise PEFormatError("Missing DOS PE header")
        pe_offset = self._unpack("<I", 0x3C)[0]
        if pe_offset < 0x40 or pe_offset > len(b) - 0x100 or b[pe_offset:pe_offset+4] != b"PE\0\0":
            raise PEFormatError("Missing or out-of-range PE signature")
        coff = pe_offset + 4
        machine, section_count = self._unpack("<HH", coff)
        optional_size = self._unpack("<H", coff+16)[0]
        optional_offset = coff + 20
        if machine != 0x8664 or self._unpack("<H", optional_offset)[0] != 0x20B:
            raise PEFormatError("Requires an x64 PE32+ image")
        if section_count < 1 or section_count > 96 or optional_size < 0x70:
            raise PEFormatError("Unexpected section count or optional header")
        self.image_base = self._unpack("<Q", optional_offset+24)[0]
        self.import_directory_rva = self._unpack("<I",optional_offset+120)[0] if optional_size>=128 else 0
        section_start = optional_offset + optional_size
        if section_start + section_count*40 > len(b):
            raise PEFormatError("Truncated section table")
        self.sections = []
        for i in range(section_count):
            o = section_start+i*40
            name, size, rva, nbytes, pos, _, _, _, _, flags = self._unpack("<8sIIIIIIHHI", o)
            if nbytes and (pos > len(b) or nbytes > len(b)-pos):
                raise PEFormatError("Truncated or overflowing section contents")
            self.sections.append(Section(name.rstrip(b"\x00").decode("ascii","replace"),rva,size,pos,nbytes,flags))
        self.sha256 = hashlib.sha256(b).hexdigest()

    def _unpack(self, fmt, offset):
        n = struct.calcsize(fmt)
        if offset < 0 or offset+n > len(self.data):
            raise PEFormatError("Out-of-bounds PE read")
        return struct.unpack_from(fmt, self.data, offset)

    def section(self, name):
        return next((s for s in self.sections if s.name==name),None)

    def at_rva(self, rva, n=1, *, executable=False):
        if rva < 0 or n < 0:
            raise PEFormatError("Negative RVA/size")
        for s in self.sections:
            if s.rva <= rva and rva-s.rva <= s.file_size and n <= s.file_size-(rva-s.rva):
                if executable and not s.executable:
                    raise PEFormatError("RVA is not executable")
                pos = s.file_offset+rva-s.rva
                return self.data[pos:pos+n]
        raise PEFormatError("RVA not backed by original file bytes")

    def cstring_rva(self,rva,max_length=512):
        if max_length < 1 or max_length > 4096:
            raise PEFormatError("Unreasonable string length")
        containing=next((section for section in self.sections
                         if section.rva<=rva<section.rva+section.file_size),None)
        if containing is None:raise PEFormatError("String RVA not backed")
        raw=self.at_rva(rva,min(max_length,containing.file_size-(rva-containing.rva)))
        e=raw.find(b"\0")
        if e<0:raise PEFormatError("Unterminated bounded C string")
        return raw[:e].decode("ascii","replace")

    def imports(self):
        """IAT slot RVA -> DLL/symbol, with hard caps on malformed input."""
        found={}
        if not self.import_directory_rva:return found
        for i in range(256):
            pos=self.import_directory_rva+20*i
            oft,timestamp,chain,dll,iat=struct.unpack("<IIIII",self.at_rva(pos,20))
            if not any((oft,timestamp,chain,dll,iat)):
                return found
            if not dll or not iat:
                raise PEFormatError("Incomplete import descriptor")
            dllname=self.cstring_rva(dll)
            thunks=oft or iat
            for n in range(8192):
                pointer=struct.unpack("<Q",self.at_rva(thunks+8*n,8))[0]
                if pointer==0:break
                if pointer>>63:
                    name="#"+str(pointer&0xffff)
                else:
                    if pointer >= 1<<32:
                        raise PEFormatError("Unexpected 64-bit import name RVA")
                    name=self.cstring_rva(pointer+2)
                found[iat+8*n]={"dll":dllname,"symbol":name}
            else: raise PEFormatError("Import thunk count exceeded safety limit")
        raise PEFormatError("Import descriptor count exceeded safety limit")

    def u32(self,rva): return struct.unpack("<I",self.at_rva(rva,4))[0]
    def f32(self,rva): return struct.unpack("<f",self.at_rva(rva,4))[0]
    def inventory(self):
        return {
            "name":self.path.name, "bytes":len(self.data), "sha256":self.sha256,
            "image_base":hex(self.image_base),
            "sections":[{"name":s.name,"rva":hex(s.rva),"file_size":s.file_size,
                         "virtual_size":s.virtual_size,"executable":s.executable} for s in self.sections]
        }
