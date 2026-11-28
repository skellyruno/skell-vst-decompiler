"""Read-only PE32 metadata inventory; no plugin loading or code execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


class LegacyPE:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        b = self.data
        if len(b) < 256 or b[:2] != b'MZ':
            raise ValueError('Missing DOS header')
        pe, = self.unpack('<I', 60)
        if pe < 64 or b[pe:pe+4] != b'PE\0\0':
            raise ValueError('Invalid PE signature')
        machine, count, self.timestamp, _, _, optsize, flags = self.unpack('<HHIIIHH', pe+4)
        opt = pe+24
        if machine != 0x14c or not 1 <= count <= 96 or optsize < 96 or self.unpack('<H',opt)[0] != 0x10b:
            raise ValueError('Expected x86 PE32')
        self.dll = bool(flags & 0x2000)
        self.base, = self.unpack('<I',opt+28)
        n, = self.unpack('<I',opt+92)
        if n > (optsize-96)//8:
            raise ValueError('Truncated data directories')
        self.directories = [self.unpack('<II',opt+96+i*8) for i in range(min(n,16))]
        self.sections = []
        for i in range(count):
            name, vs, rva, size, off, _, _, _, _, flags = self.unpack('<8sIIIIIIHHI',opt+optsize+i*40)
            if size and (off+size > len(b) or rva+size > 2**32):
                raise ValueError('Section outside file or RVA space')
            self.sections.append({'name':name.rstrip(b'\0').decode('ascii','replace'), 'rva':rva,
                                  'size':size,'offset':off,'virtual_size':vs,'executable':bool(flags&0x20000000)})
        self.sha256 = hashlib.sha256(b).hexdigest()

    def unpack(self, fmt, off):
        if off < 0 or off+struct.calcsize(fmt)>len(self.data):
            raise ValueError('Out-of-bounds header read')
        return struct.unpack_from(fmt,self.data,off)

    def read(self,rva,size):
        if rva<0 or size<0:
            raise ValueError('Invalid range')
        matches=[s for s in self.sections if s['rva']<=rva and rva-s['rva']+size<=s['size']]
        if len(matches)!=1:
            raise ValueError('RVA not uniquely file backed')
        s=matches[0]; off=s['offset']+rva-s['rva']
        return self.data[off:off+size]

    def directory(self,index):
        return self.directories[index] if index<len(self.directories) else (0,0)

    def exports(self):
        rva,size=self.directory(0)
        if not rva and not size:
            return {'named_count':0,'address_count':0,'public_vst_entries':[]}
        if not rva or size<40:
            raise ValueError('Invalid export directory')
        _,_,_,_,_,_,nf,nn,funcs,names,ords=struct.unpack('<IIHHIIIIIII',self.read(rva,40))
        if not 0<=nn<=nf<=65536:
            raise ValueError('Invalid export counts')
        public=[]
        for i in range(nn):
            ptr,=struct.unpack('<I',self.read(names+4*i,4))
            ordinal,=struct.unpack('<H',self.read(ords+2*i,2))
            if ordinal>=nf:
                raise ValueError('Invalid export ordinal')
            # Read only the two public VST2 entry names; no private symbol dump.
            for name in ('VSTPluginMain','main'):
                try:
                    exact=self.read(ptr,len(name)+1)==name.encode()+b'\0'
                except ValueError:
                    exact=False
                if exact:
                    target,=struct.unpack('<I',self.read(funcs+4*ordinal,4))
                    public.append({'name':name,'rva':hex(target),'forwarded':rva<=target<rva+size})
        return {'named_count':nn,'address_count':nf,'public_vst_entries':public}

    def inventory(self):
        return {'schema_version':1,'report_kind':'legacy_pe_metadata','binary_sha256':self.sha256,
                'bytes':len(self.data),'architecture':'x86','format':'PE32','dll':self.dll,
                'image_base':hex(self.base),'coff_timestamp':self.timestamp,
                'section_count':len(self.sections),'executable_section_count':sum(s['executable'] for s in self.sections),
                'has_exception_directory':bool(self.directory(3)[0]),'exports':self.exports(),
                'note':'File metadata only; not verified runtime identity or DSP behavior.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary',type=Path)
    print(json.dumps(LegacyPE(p.parse_args().binary).inventory(),indent=2,sort_keys=True))


if __name__=='__main__':main()
