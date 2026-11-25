"""Owned exact-build Linux x64 VST3 controller inventory, via public SDK interfaces only."""
import ctypes as c,hashlib,json,platform,struct,sys
from pathlib import Path
EXPECTED='82edf9789d1f2632f6f707ee9739f9d1e54f9e5e0781d829a9016ddc513876c3'
P=c.c_void_p; I=c.c_int32; U=c.c_uint32
class ClassInfo(c.Structure):
    _fields_=[('cid',c.c_ubyte*16),('cardinality',I),('category',c.c_char*32),('name',c.c_char*64)]
class ParameterInfo(c.Structure):
    _fields_=[('id',U),('title',c.c_uint16*128),('shortTitle',c.c_uint16*128),('units',c.c_uint16*128),('stepCount',I),('defaultNormalizedValue',c.c_double),('unitId',I),('flags',I)]
def uid(*words):return struct.pack('>4I',*words)
COMPONENT=uid(0xE831FF31,0xF2D54301,0x928EBBEE,0x25697802)
CONTROLLER=uid(0xDCD7BBE3,0x7742448D,0xA874AACC,0x979C759E)
CONNECTION=uid(0x70A4156F,0x6E6E4026,0x989148BF,0xAA60D8D1)
def invoke(obj,index,ret,args,*values):
    table=c.cast(obj,c.POINTER(c.POINTER(P))).contents
    return c.CFUNCTYPE(ret,P,*args)(table[index])(obj,*values)
def ok(value):
    if value!=0:raise RuntimeError(f'VST3 error {value}')
def query(obj,iid):
    p=P();ok(invoke(obj,0,I,[c.c_char_p,c.POINTER(P)],iid,c.byref(p)))
    if not p:raise RuntimeError('Null interface')
    return p
def create(factory,cid,iid):
    p=P();ok(invoke(factory,6,I,[c.c_char_p,c.c_char_p,c.POINTER(P)],cid,iid,c.byref(p)))
    if not p:raise RuntimeError('Null instance')
    return p
def string16(value):return bytes(value).decode('utf-16-le').split('\0',1)[0]
def inventory(path):
    path=Path(path).resolve()
    if platform.system()!='Linux' or platform.machine()!='x86_64' or c.sizeof(P)!=8 or hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Only exact owned x64 Linux build permitted')
    if c.sizeof(ClassInfo)!=116 or c.sizeof(ParameterInfo)!=792:raise ValueError('Unexpected SDK struct layout')
    lib=c.CDLL(str(path));lib.ModuleEntry.argtypes=[P];lib.ModuleEntry.restype=c.c_bool
    lib.ModuleExit.argtypes=[];lib.ModuleExit.restype=c.c_bool
    lib.GetPluginFactory.argtypes=[];lib.GetPluginFactory.restype=P
    if not lib.ModuleEntry(lib._handle):raise RuntimeError('Module entry failed')
    f=lib.GetPluginFactory();objects=[];initialized=[];connections=[]
    try:
        if not f:raise RuntimeError('Null factory')
        n=invoke(f,4,I,[])
        if not 1<=n<=32:raise ValueError('Unexpected classes')
        classes=[]
        for i in range(n):
            info=ClassInfo();ok(invoke(f,5,I,[c.c_int32,c.POINTER(ClassInfo)],i,c.byref(info)));classes.append(info)
        audio=[x for x in classes if x.category==b'Audio Module Class'];controls=[x for x in classes if x.category==b'Component Controller Class']
        if len(audio)!=1 or len(controls)!=1:raise ValueError('Ambiguous owned classes')
        component=create(f,bytes(audio[0].cid),COMPONENT);objects.append(component)
        ok(invoke(component,3,I,[P],None));initialized.append(component)
        cid=(c.c_ubyte*16)();ok(invoke(component,5,I,[P],c.byref(cid)))
        if bytes(cid)!=bytes(controls[0].cid):raise ValueError('Controller class mismatch')
        controller=create(f,bytes(cid),CONTROLLER);objects.append(controller)
        ok(invoke(controller,3,I,[P],None));initialized.append(controller)
        cp=query(component,CONNECTION);objects.append(cp);ep=query(controller,CONNECTION);objects.append(ep)
        ok(invoke(cp,3,I,[P],ep));connections.append((cp,ep))
        ok(invoke(ep,3,I,[P],cp));connections.append((ep,cp))
        n=invoke(controller,8,I,[])
        if not 1<=n<=2048:raise ValueError('Unexpected parameter count')
        rows=[]
        for i in range(n):
            info=ParameterInfo();ok(invoke(controller,9,I,[I,c.POINTER(ParameterInfo)],i,c.byref(info)))
            rows.append({'index':i,'id':info.id,'title':string16(info.title),'units':string16(info.units),'steps':info.stepCount,'default_normalized':info.defaultNormalizedValue,'flags':info.flags})
        if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate parameter IDs')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Module changed')
        return {'module_sha256':EXPECTED,'interface':'VST3 IEditController::getParameterInfo','platform':'Linux x86_64','parameters':rows}
    finally:
        for x,y in reversed(connections):invoke(x,4,I,[P],y)
        for x in reversed(initialized):invoke(x,4,I,[])
        for x in reversed(objects):invoke(x,2,U,[])
        if f:invoke(f,2,U,[])
        lib.ModuleExit()
if __name__=='__main__':print(json.dumps(inventory(sys.argv[1]),indent=2,allow_nan=False))
