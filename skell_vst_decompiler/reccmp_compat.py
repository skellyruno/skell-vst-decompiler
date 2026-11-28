"""Independent PE export-table reader for the pinned standalone Reccmp CLI.

Only the exports property is replaced in this opt-in process. No upstream
source is vendored. The compatibility CLI is tested on owned fixtures only.
"""
import struct
from functools import cached_property


def named_exports(read, read_string, image_base, directory_va):
    """Resolve names through the PE name-pointer and ordinal arrays."""
    header=struct.unpack('<IIHHIIIIIII',read(directory_va,40))
    nf,nn,functions,names,ordinals=header[6:11]
    if nf>65536 or nn>65536 or (nn and not nf):
        raise ValueError('Unexpected PE export counts')
    if not nn:
        return []
    if not all((functions,names,ordinals)):
        raise ValueError('Missing PE export array')
    targets=struct.unpack('<'+'I'*nf,read(image_base+functions,4*nf))
    pointers=struct.unpack('<'+'I'*nn,read(image_base+names,4*nn))
    indices=struct.unpack('<'+'H'*nn,read(image_base+ordinals,2*nn))
    result=[]
    seen=set()
    for pointer,index in zip(pointers,indices):
        if index>=nf or not pointer or not targets[index]:
            raise ValueError('Invalid named export entry')
        name=read_string(image_base+pointer)
        if not isinstance(name,bytes) or not name or name in seen:
            raise ValueError('Invalid or repeated export name')
        seen.add(name)
        result.append((image_base+targets[index],name))
    return result


def main():
    from reccmp.formats.pe import PEImage,PEDataDirectoryItemType
    from reccmp.tools.verexp import main as verexp

    def corrected(image):
        region=image.get_data_directory_region(PEDataDirectoryItemType.EXPORT_TABLE)
        if not region:
            return []
        return named_exports(image.read,image.read_string,image.imagebase,region.virtual_address)

    property_=cached_property(corrected)
    property_.__set_name__(PEImage,'exports')
    PEImage.exports=property_
    return verexp()


if __name__=='__main__':
    raise SystemExit(main())
