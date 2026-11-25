import struct
import unittest
from skell_vst_decompiler.owned_state import ALPHABET,decode_block,juce_param_id,master_state,compare_master


def wrap(x, tail=b'\0'):
    b=x.encode();return b'VC2!'+struct.pack('<I',len(b))+b+tail


def enc(raw):
    n=int.from_bytes(raw,'little')
    return str(len(raw))+'.'+''.join(ALPHABET[(n>>i)&63] for i in range(0,len(raw)*8,6))


def state(value, tail=b'\0opaque'):
    inner=wrap(f'<SKELLY_MASTER_PARAMETERS skellMasterStateVersion="16"><PARAM id="input" value="{value}"/></SKELLY_MASTER_PARAMETERS>',tail)
    return wrap('<VST3PluginState><IComponent>'+enc(inner)+'</IComponent></VST3PluginState>')


class OwnedStateTests(unittest.TestCase):
    def test_hash(self):
        self.assertEqual(juce_param_id('gain'),3165055)
        self.assertEqual(juce_param_id('input'),100358090)
        self.assertEqual(juce_param_id('creative_delay'),juce_param_id('creative_delay',False)&0x7fffffff)
        with self.assertRaises(ValueError):juce_param_id('')

    def test_codec(self):
        for n in range(1,64):
            b=bytes(range(n));self.assertEqual(decode_block(enc(b)),b)
        for s in ('1.','1.!!','1.++','999999999.A'):
            with self.assertRaises(ValueError):decode_block(s)

    def test_state(self):
        a,b=state(0),state(6)
        self.assertEqual(master_state(b)['parameters']['input'],6)
        self.assertEqual(compare_master(a,b),dict(changed_parameters=['input'],properties_equal=True,opaque_equal=True))
        self.assertFalse(compare_master(a,state(6,b'other'))['opaque_equal'])
        with self.assertRaises(ValueError):master_state(b'bad')
