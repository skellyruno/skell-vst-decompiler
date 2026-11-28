"""Run pinned standalone Craft Anything only on freshly generated owned PE fixtures."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.craft_metadata import compare_owned,MAX_BYTES


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cli',type=Path,required=True)
    cli=p.parse_args().cli.resolve()
    with tempfile.TemporaryDirectory(prefix='skell-craft-') as d:
        root=Path(d)
        # Do not forward API keys, agent credentials or persistent local configuration.
        home=root/'home';home.mkdir()
        env={'PATH':os.environ['PATH'],'HOME':str(home),'XDG_CONFIG_HOME':str(home/'config'),
             'XDG_DATA_HOME':str(home/'data'),'XDG_CACHE_HOME':str(home/'cache'),
             'TMPDIR':str(root),'LANG':'C.UTF-8'}
        def command(args,expected=0):
            out=subprocess.run([str(cli),*args],cwd=root,env=env,capture_output=True,timeout=90)
            if out.returncode!=expected:
                raise RuntimeError('Craft CLI exit '+str(out.returncode)+': '+(out.stderr+out.stdout)[:2000].decode('utf-8','replace'))
            if len(out.stdout)>MAX_BYTES:
                raise RuntimeError('Oversized owned evidence')
            return out.stdout
        version=command(['--version']).decode().strip()
        if '0.6.1' not in version:
            raise RuntimeError('Unexpected Craft version: '+version)
        cases=[]
        for arch,target,machine in [('x86','i686-pc-windows-msvc','x86'),('x64','x86_64-pc-windows-msvc','x64')]:
            for opt in ('O0','O2'):
                src=root/'fixture.c';obj=root/'fixture.obj';dll=root/'fixture.dll'
                src.write_text('__declspec(dllexport) int probe(int x){return x*3+1;}\n')
                subprocess.run(['clang','--target='+target,'-'+opt,'-c',str(src),'-o',str(obj)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),str(obj)],check=True,timeout=30)
                # No --allow-run, AI backend, setup, rebuild, runtime tool, or MCP server.
                raw=command(['--deep','native-layout-show','--path',str(dll),'--detail','complete','--output-format','json'])
                row=compare_owned(raw,dll)
                if not row['agreed']:
                    raise RuntimeError('Owned fixture metadata disagreement: '+json.dumps(row))
                # Upstream validates its own evidence ID using the documented inline browsing route.
                evidence=json.loads(raw)
                request=root/'browse.json'
                def browse(record,expected):
                    request.write_text(json.dumps({'source':{'kind':'inline','evidence':record},'show':{'kind':'summary'}}))
                    return json.loads(command(['--deep','core-evidence-browse','--json','@'+str(request),'--output-format','json'],expected))
                browse(evidence,0)
                evidence['result']['bits']=128
                rejected=browse(evidence,1)
                if 'error' not in rejected:
                    raise RuntimeError('Upstream did not return structured tamper error')
                cases.append({'architecture':arch,'optimization':opt,'metadata':row,
                              'upstream_inline_integrity_check':True,'tampered_record_rejected':True})
        print('SKELL_CRAFT_RESULT '+json.dumps({'version':version,'cases':cases,'all_agreed':True},sort_keys=True))


if __name__=='__main__':main()
