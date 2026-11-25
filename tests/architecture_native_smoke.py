"""Compile a freestanding owned two-DLL fixture and check its static import edge."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from skell_vst_decompiler.architecture_intake import architecture


def main():
    tools = [shutil.which(x) for x in ('clang', 'lld-link', 'objdump')]
    if not all(tools):
        raise RuntimeError('clang, lld-link and GNU objdump required')
    clang, link, objdump = tools
    fixtures = Path(__file__).resolve().parent / 'fixtures'
    with tempfile.TemporaryDirectory(prefix='skell-arch-fixture-') as tmp:
        root = Path(tmp)
        for name in ('engine', 'wrapper'):
            subprocess.run([clang, '--target=x86_64-pc-windows-msvc', '-O2', '-c',
                            str(fixtures / ('architecture_' + name + '.c')), '-o', name + '.obj'],
                           cwd=root, check=True, timeout=30)
            args = [link, '/dll', '/noentry', '/nodefaultlib', '/out:' + name + '.dll', name + '.obj']
            args += ['/implib:engine.lib'] if name == 'engine' else ['engine.lib']
            subprocess.run(args, cwd=root, check=True, timeout=30)
        result = architecture(root/'wrapper.dll', [root/'engine.dll'])
        assert result['adjacent_candidates'][0]['status'] == 'STATIC_IMPORT'
        report = subprocess.check_output([objdump, '-p', str(root/'wrapper.dll')], text=True, timeout=30)
        assert 'DLL Name: engine.dll' in report and 'CreateEngine' in report
        print('Owned wrapper/engine static import edge agrees with GNU objdump.')


if __name__ == '__main__':
    main()
