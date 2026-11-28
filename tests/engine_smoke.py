"""Compile our owned fixture and compare actual GNU and LLVM disassembly."""
import json
from pathlib import Path
import subprocess
import tempfile
from ghidra_smoke import fixture_exports
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.navigation import runtime_ranges, containing_range
from skell_vst_decompiler.engine_agreement import call_observations, compare


def main():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        obj, exe = root/'fixture.obj', root/'fixture.exe'
        source = Path(__file__).parent/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)], check=True, timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)], check=True, timeout=30)
        pe = PE(exe)
        exports = fixture_exports(exe)
        start = exports['apply_gain']
        span = containing_range(runtime_ranges(pe), start)
        if span is None or int(span['start_rva'],16) != start:
            raise RuntimeError('Fixture unwind span missing')
        a = call_observations(pe, start, span['bytes'], 'objdump')
        b = call_observations(pe, start, span['bytes'], 'llvm-objdump')
        checks = compare(a,b)
        if not checks or any(x['status'] != 'agreed_static' for x in checks) or not any(x['left_target'] == hex(exports['smooth']) for x in checks):
            raise RuntimeError('Owned fixture engine mismatch: '+json.dumps(checks))
        print(json.dumps({'fixture_sha256': pe.sha256, 'exports': exports, 'checks': checks,
                          'engines': {e: subprocess.check_output([e,'--version'],text=True,timeout=10).splitlines()[0] for e in ('objdump','llvm-objdump')}}, indent=2))


if __name__ == '__main__':
    main()
