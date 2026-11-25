"""Known JUCE owned-state format, read-only; numeric IDs are source predictions."""
import struct
import xml.etree.ElementTree as ET
import math

MAX_BYTES = 4 * 1024 * 1024
ALPHABET = '.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'


def juce_param_id(key, studio_one=True):
    if not isinstance(key, str) or not 1 <= len(key) <= 256 or not key.isascii():
        raise ValueError('Expected bounded ASCII source parameter ID')
    h = 0
    for c in key:
        h = (31*h+ord(c)) & 0xffffffff
    return h & (0x7fffffff if studio_one else 0xffffffff)


def decode_block(text):
    if not isinstance(text, str) or len(text) > 2*MAX_BYTES:
        raise ValueError('Invalid block')
    prefix, sep, encoded = text.partition('.')
    if not sep or not prefix.isascii() or not prefix.isdecimal() or len(prefix)>8:
        raise ValueError('Invalid encoded size')
    n = int(prefix)
    if not 0<n<=MAX_BYTES or len(encoded)!=(n*8+5)//6:
        raise ValueError('Encoded length mismatch')
    result=bytearray();value=bits=0
    for c in encoded:
        i=ALPHABET.find(c)
        if i<0:raise ValueError('Invalid encoded character')
        value|=i<<bits;bits+=6
        if bits>=8:
            result.append(value&255);value>>=8;bits-=8
    if len(result)!=n or value:raise ValueError('Invalid padding')
    return bytes(result)


def read_xml(raw):
    if not isinstance(raw, bytes) or not 8<=len(raw)<=MAX_BYTES or raw[:4]!=b'VC2!':
        raise ValueError('Not bounded JUCE XML state')
    length=struct.unpack_from('<I',raw,4)[0]
    if not 0<length<=len(raw)-8:raise ValueError('Invalid XML length')
    xml=raw[8:8+length]
    if b'<!' in xml:raise ValueError('XML declarations not supported')
    return ET.fromstring(xml),raw[8+length:]


def master_state(raw):
    """Strict known Master version-16 schema. Unknown bytes retained for comparison."""
    outer,tail=read_xml(raw)
    if outer.tag!='VST3PluginState' or outer.attrib or len(outer)!=1 or outer[0].tag!='IComponent':
        raise ValueError('Unexpected host state wrapper')
    root,opaque=read_xml(decode_block(outer[0].text))
    if root.tag!='SKELLY_MASTER_PARAMETERS' or root.get('skellMasterStateVersion')!='16':
        raise ValueError('Unknown Master schema')
    params={}
    for c in root:
        if c.tag!='PARAM' or set(c.attrib)!={'id','value'} or len(c) or c.get('id') in params:
            raise ValueError('Unexpected parameter field')
        value=float(c.get('value'))
        if not math.isfinite(value):raise ValueError('Nonfinite parameter')
        params[c.get('id')]=value
    return {'parameters':params,'properties':dict(root.attrib),'opaque':opaque,'outer_tail':tail}


def compare_master(a,b):
    x,y=master_state(a),master_state(b)
    if x['parameters'].keys()!=y['parameters'].keys():raise ValueError('Parameter identity changed')
    return {'changed_parameters':sorted(k for k in x['parameters'] if x['parameters'][k]!=y['parameters'][k]),
            'properties_equal':x['properties']==y['properties'],
            'opaque_equal':x['opaque']==y['opaque'] and x['outer_tail']==y['outer_tail']}
