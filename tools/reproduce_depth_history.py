"""Reproduce the additional dated law blocks from their frozen Git stream.

Start from the baseline named in data/depth-reproduction.json in a disposable
clone. This reproduces law commits and tags; documentation is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    args=parser.parse_args()
    source=Path(__file__).resolve().parents[1]/'data'
    record=json.loads((source/'depth-reproduction.json').read_text(encoding='utf-8'))
    stream=(source/'depth-history.fi').read_bytes()
    assert hashlib.sha256(stream).hexdigest()==record['stream_sha256']
    def git(*words):
        result=subprocess.run(['git','-c','gc.auto=0','-C',str(args.repo),*words],capture_output=True,text=True,encoding='utf-8')
        if result.returncode:raise RuntimeError(result.stderr)
        return result.stdout.strip()
    if git('rev-parse','HEAD')!=record['baseline']:
        raise SystemExit('Target HEAD must equal the recorded baseline; use a disposable clone.')
    if git('status','--porcelain'):
        raise SystemExit('Target checkout must be clean.')
    result=subprocess.run(['git','-c','gc.auto=0','-C',str(args.repo),'fast-import','--quiet'],input=stream,capture_output=True)
    if result.returncode:raise SystemExit(result.stderr.decode('utf-8',errors='replace'))
    head=git('rev-parse','HEAD')
    assert head==record['law_head'],(head,record['law_head'])
    for tag,commit in record['tags'].items():
        assert git('rev-parse',tag+'^{}')==commit
    print(json.dumps({'law_head_identical':True,'tags_identical':True,'head':head}))

if __name__=='__main__':main()
