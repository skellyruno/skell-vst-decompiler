"""Exact-build, read-only parameter endpoints and scoped VMR dispatch evidence."""
import hashlib
import json
import struct
from pathlib import Path
from .pe import PE
from .disasm import disassemble
from .coloration import lookup_slots
from .classgraph import class_graph
from .navigation import runtime_ranges, containing_range
from .equations import TVB_SHA256

# name, host pointer slot, load RVA, store RVA, parent field, object base
ENDPOINTS = [
    ('delay_mix',0x3b440,0x343642,0x343661,0x36db8,0x36c68),
    ('delay_time_ms',0x3b448,0x343669,0x34368e,0x36dbc,0x36c68),
    ('delay_sync_on',0x3b450,0x343696,0x3436a9,0x36dc0,0x36c68),
    ('delay_division',0x3b458,0x3436af,0x343706,0x36dc4,0x36c68),
    ('delay_feedback',0x3b460,0x34370f,0x343732,0x36dcc,0x36c68),
    ('delay_pingpong',0x3b468,0x34373a,0x34374d,0x36dd0,0x36c68),
    ('delay_lp_hz',0x3b470,0x343753,0x343781,0x36dd4,0x36c68),
    ('delay_hp_hz',0x3b478,0x343789,0x3437aa,0x36dd8,0x36c68),
    ('delay_duck',0x3b480,0x3437c4,0x3437e8,0x36ddc,0x36c68),
    ('delay_duck_on',0x3b488,0x3437b2,0x3437e8,0x36ddc,0x36c68),
    ('fx_delay_division',0x210,0x3443ab,0x34440d,0x36dc4,0x36c68),
    ('lim_ceiling_db',0x3b4f0,0x343a60,0x343a80,0x37b30,0x379e0),
    ('lim_release_ms',0x3b4f8,0x343a88,0x343aaa,0x37b34,0x379e0),
    ('lim_auto_release',0x3b500,0x343ab2,0x343ac5,0x37b38,0x379e0),
    ('lim_drive_db',0x3b508,0x343acb,0x343ae6,0x37b3c,0x379e0),
    ('lim_true_peak',0x3b510,0x343aee,0x343b01,0x37b40,0x379e0),
    ('lim_mode',0x3b518,0x343b07,0x343b2c,0x37b44,0x379e0),
]


def tvb_endpoints(pe):
    if pe.sha256 != TVB_SHA256:
        raise ValueError('Unexpected TVB source fingerprint')
    host = disassemble(pe,0x33baa0,0x63b7)
    slots = {x['name']: x for x in lookup_slots(pe,host)}
    process = disassemble(pe,0x342840,0x229d)
    by = {x.address-pe.image_base:x for x in process}
    out = []
    for name,slot,load,store,field,base in ENDPOINTS:
        row = slots[name]
        actual = int(row['slot_offset'],16)
        if row['literal_base']=='rbx' and name=='fx_delay_division':
            actual += 0x160
        elif row['literal_base']!='r15':
            raise ValueError('Unexpected host pointer base')
        if actual != slot or by[load].text != f'mov rax,QWORD PTR [rdi+{slot:#x}]':
            raise ValueError('Unexpected source endpoint')
        if not by[store].operands.startswith((f'DWORD PTR [rdi+{field:#x}],',f'BYTE PTR [rdi+{field:#x}],')):
            raise ValueError('Unexpected store endpoint')
        out.append(dict(name=name,slot=hex(slot),load=hex(load),store=hex(store),object_field=hex(field-base)))
    return out


def module_dispatch(pe):
    """Return scoped slot-8 wrappers and their first r15 table; not runtime selection."""
    rows = []
    for c in class_graph(pe,'ModuleProcessor')['classes']:
        for t in c['vtables']:
            for m in t['candidate_slots']:
                if m['slot'] != 8 or not m['unwind_region']:
                    continue
                start=int(m['rva'],16)
                region=m['unwind_region']
                if start != int(region['start_rva'],16) or region['bytes'] > 2048:
                    continue
                ins=disassemble(pe,start,region['bytes'])
                tables=[i for i in ins if i.mnemonic=='lea' and i.operands.startswith('r15,[rip') and '# 0x' in i.operands]
                if len(tables)!=1:
                    continue
                table=int(tables[0].operands.split('#')[-1].strip(),16)-pe.image_base
                pair=[v-pe.image_base for v in struct.unpack('<2Q',pe.at_rva(table+32,16))]
                for v in pair:
                    pe.at_rva(v,1,executable=True)
                calls=[hex(i.address-pe.image_base) for i in ins if i.mnemonic=='call' and i.operands in ('QWORD PTR [r15+rdx*8]','QWORD PTR [rsi+rdx*8]')]
                rows.append(dict(wrapper=hex(start),vtable=t['vtable_rva'],table=hex(table),slots_4_5=list(map(hex,pair)),indexed_calls=calls))
    return {'binary_sha256':pe.sha256,'rows':rows}


def inventory(directory):
    return [{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in sorted(Path(directory).glob('*.epl'))]


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tvb',type=Path)
    parser.add_argument('modules',type=Path)
    args=parser.parse_args()
    names=['FG-116','FG-2A','FG-Stress','FG-401','AirEQAir','AirEQEarth','VCC Channel','VCC MixBuss']
    print(json.dumps({'tvb':tvb_endpoints(PE(args.tvb)),'inventory':inventory(args.modules),'modules':{n:module_dispatch(PE(args.modules/(n+'.epl'))) for n in names}},sort_keys=True,indent=2))
