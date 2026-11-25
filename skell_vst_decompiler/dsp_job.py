"""Private static discovery job for the Analyzer front end; no target execution."""
import argparse
import json
from pathlib import Path
import shutil
from .dsp_discovery import discover


def run_job(binary, output):
    binary,output=Path(binary),Path(output)
    if not binary.is_absolute() or not output.is_absolute() or output.suffix.lower()!='.json':
        raise ValueError('Absolute module and JSON output paths required')
    if output.exists() or output.is_symlink():raise ValueError('Report destination already exists')
    tool=next((t for t in ('objdump','llvm-objdump') if shutil.which(t)),None)
    try:
        if tool is None:raise RuntimeError('Install GNU or LLVM objdump on PATH')
        report=discover(binary,limit=32,tool=tool)
        status=0
    except (ValueError,OSError,RuntimeError) as exc:
        report={'schema_version':1,'type':'dsp_discovery_error','error':str(exc)[:300]}
        status=1
    content=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if len(content.encode('utf8'))>512*1024:raise ValueError('Report exceeds viewer bound')
    with output.open('x',encoding='utf8') as stream:stream.write(content)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();return run_job(a.binary,a.output)


if __name__=='__main__':raise SystemExit(main())
