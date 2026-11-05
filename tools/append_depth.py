"""Append source-backed evidence, contracts, criminal procedure and companies history.

The target must be a disposable clone of the published baseline. Existing law
files and tags are preserved. Source inputs are required; no network is used.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import depth_history as D

HERE = Path(__file__).resolve().parent

def git(repo, *args, data=None, binary=False):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-C', str(repo), *args], input=data, capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode('utf-8').strip()

def block(body):
    body = body.encode('utf-8') if isinstance(body, str) else body
    return b'data ' + str(len(body)).encode() + b'\n' + body + b'\n'

def append(repo, source_dir, today):
    repo = Path(repo)
    baseline = git(repo, 'rev-parse', 'HEAD')
    assert not git(repo, 'status', '--porcelain'), 'Target must be clean'
    snapshots = D.snapshots(source_dir)
    problems, checks = D.check_sources(source_dir)
    assert not problems, problems
    for record, files, changes in snapshots:
        assert not git(repo, 'tag', '--list', record['tag']), 'An added tag already exists'
    for key in ['AUTHOR', 'COMMITTER']:
        os.environ['GIT_' + key + '_NAME'] = 'Lexifina'
        os.environ['GIT_' + key + '_EMAIL'] = 'rwanda-law@lexifina.com'
    clock = int(git(repo, 'show', '-s', '--format=%ct', 'HEAD'))
    stream = bytearray()
    previous = baseline
    states = {}
    for index, (record, files, changes) in enumerate(snapshots, 1):
        act = record['act']
        before = states.get(act, {})
        changed = {name: files.get(name) for name in sorted(set(files) | set(before)) if files.get(name) != before.get(name)}
        states[act] = files
        day = record['from']
        clock += 1
        author_time = int(dt.datetime.fromisoformat(day + 'T12:00:00+02:00').timestamp())
        message = (record['law'] + ': ' + act + ' (' + record['history'] + ')\n\n'
                   'English Official Gazette text; dated by its own commencement and publication.\n\n'
                   'Kind: Law' + (' (amending)' if record['history'] == 'replayed' else '') + '\n'
                   'In-force: ' + day + '\nPublished: ' + day + '\n'
                   'In-force-basis: ' + record['in_force_basis'] + '\nAct-path: ' + act + '\n'
                   'Source: ' + record['source_url'] + '\nSource-sha256: ' + record['source_sha256'] + '\n')
        stream.extend(f'commit refs/heads/main\nmark :{index}\n'.encode())
        stream.extend(f"author {record['law']} <law-{record['tag'].split('/')[-1]}@amategeko.invalid> {author_time} +0200\n".encode())
        stream.extend(f'committer Lexifina <rwanda-law@lexifina.com> {clock} +0000\n'.encode())
        stream.extend(block(message))
        stream.extend(f'from {previous}\n'.encode())
        for name, text in changed.items():
            if text is None:
                stream.extend(f'D {act}/{name}\n'.encode())
            else:
                stream.extend(f'M 100644 inline {act}/{name}\n'.encode())
                stream.extend(block(text))
        stream.extend(b'\n')
        previous = f':{index}'
        stream.extend(f"tag {record['tag']}\nfrom {previous}\ntagger Lexifina <rwanda-law@lexifina.com> {clock} +0000\n".encode())
        stream.extend(block(f"{record['law']}; in force {day}\n"))
    git(repo, 'fast-import', '--quiet', data=bytes(stream))
    git(repo, 'reset', '--hard', 'HEAD')
    law_head = git(repo, 'rev-parse', 'HEAD')
    tags = {record['tag']: git(repo, 'rev-parse', record['tag'] + '^{}') for record, _, _ in snapshots}
    frozen = git(repo, 'fast-export', '--reference-excluded-parents', '--show-original-ids', law_head,
                 *['refs/tags/' + tag for tag in tags], '^' + baseline, binary=True)
    frozen = re.sub(rb'(?m)^commit [^\n]+', b'commit refs/heads/main', frozen)
    frozen = re.sub(rb'(?m)^reset [0-9a-f]{40}', b'reset refs/heads/main', frozen)
    record = {'baseline': baseline, 'law_head': law_head, 'law_commits': 6, 'versions': 6, 'acts': 4,
              'tags': tags, 'stream_sha256': hashlib.sha256(frozen).hexdigest()}
    corpus = json.loads((repo / 'corpus.json').read_text(encoding='utf-8'))
    corpus['acts'] += list(states)
    corpus['depth_versions'] = 'data/depth-versions.json'
    corpus['record_note'] += ' Four additional selected acts are provided as enacted, with the 2023 criminal procedure and companies amendments replayed. Complete national coverage and all subsequent amendments are not asserted.'
    readme = (repo / 'README.md').read_text(encoding='utf-8')
    readme += '\n\n## Additional dated history\n\nEvidence, contracts, criminal procedure and companies extend this selected collection. First versions are official texts as enacted; the criminal procedure and companies records replay their named 2023 amendments. Every date follows the source publication and commencement. National coverage and identification of every later amendment remain incomplete.\n\n| Folder | Versions | In force |\n| --- | ---: | --- |\n'
    for act in states:
        versions = [version for version in D.VERSIONS if version['act'] == act]
        readme += f'| `{act}/` | {len(versions)} | ' + ', '.join(version['from'] for version in versions) + ' |\n'
    readme += '\nSources are the English columns of the Official Gazette PDFs supplied by the Rwanda Law Reform Commission; the Ministry of Justice publishes the Gazette. No OCR is used. These six source texts contain no normative images; the evidence and companies covers carry decorative national emblems. See `data/depth-versions.json` and `REPRODUCE.md`.\n'
    reproduce = (repo / 'REPRODUCE.md').read_text(encoding='utf-8')
    reproduce = re.sub(r'(?m)^2026-10-28\..*$', '2026-10-28.', reproduce)
    reproduce += '\n\n## Additional source-backed history\n\nThe original build above describes the Constitution and public servants statute. Six appended law commits add four acts, with all base files reconstructed from official text-layer PDFs and both amendments replayed. Chapter, section and subsection context is retained. Complete bodies and restatements are checked against an independent PDF word-position stream.\n\nIn a disposable clone at the baseline in `data/depth-reproduction.json`, reconstruct the additional source-backed history with `python tools/build.py --append-depth --repo <clone> --source-dir <official-input-dir> --today ' + today + '`. Official inputs are the twelve PDFs named `file-<id>.pdf` and the six original metadata files named `meta-<id>.json`; source identifiers and SHA-256 values are recorded in this file and `data/depth-versions.json`. No previously parsed data is an input.\n\nValidate the complete collection with `python tools/check_repo.py --repo <clone> --source-dir <official-input-dir>` and `python tools/test_repo.py --repo <clone>`. The checker requires exactly twelve source-backed law commits, checks all files and validates the six added source digests and tags. Missing inputs or unknown replay grammar fail. The frozen law block can also be reproduced with `python tools/reproduce_depth_history.py --repo <baseline-clone>`; that verifies hashes and tags only, separately from official-source checks.\n\nAI assistance authored code and documentation. No model wrote, translated or corrected legal text, and no OCR is used.\n'
    tool_names = git(repo, 'ls-tree', '-r', '--name-only', baseline, '--', 'tools').splitlines()
    tool_names += ['tools/append_depth.py', 'tools/depth_history.py', 'tools/reproduce_depth_history.py']
    tool_root = HERE
    files = {name: (tool_root / name.split('/', 1)[1]).read_bytes() for name in tool_names}
    files.update({'README.md': readme.encode(), 'REPRODUCE.md': reproduce.encode(),
                  'corpus.json': (json.dumps(corpus, ensure_ascii=False, indent=2) + '\n').encode(),
                  'jurisdiction.json': (json.dumps({'path': 'rw', 'code': 'RW', 'name': 'Rwanda', 'level': 'country', 'repo': 'https://github.com/lexifina/rwanda-law', 'build': 'selected collection: 6 acts; official enacted texts, revisions and source-backed amendment replays; national coverage incomplete'}, indent=2) + '\n').encode(),
                  'data/depth-versions.json': (json.dumps(D.VERSIONS, ensure_ascii=False, indent=2) + '\n').encode(),
                  'data/depth-history.fi': frozen,
                  'data/depth-reproduction.json': (json.dumps(record, indent=2) + '\n').encode()})
    stamp = int(dt.datetime.fromisoformat(today + 'T12:00:00+02:00').timestamp())
    docs = bytearray(b'commit refs/heads/main\n')
    docs.extend(f'author Lexifina <rwanda-law@lexifina.com> {stamp} +0200\ncommitter Lexifina <rwanda-law@lexifina.com> {clock + 1} +0000\n'.encode())
    docs.extend(block('Documentation: source-backed depth history and complete-collection gates\n\nKind: documentation\nIn-force: ' + today + '\n'))
    docs.extend(f'from {law_head}\n'.encode())
    for name, body in sorted(files.items()):
        docs.extend(f'M 100644 inline {name}\n'.encode())
        docs.extend(block(body))
    docs.extend(b'\n')
    git(repo, 'fast-import', '--quiet', data=bytes(docs))
    git(repo, 'reset', '--hard', 'HEAD')
    return {'baseline': baseline, 'head': git(repo, 'rev-parse', 'HEAD'), 'law_head': law_head,
            'acts_added': 4, 'versions_added': 6, 'law_commits_added': 6, 'documentation_commits_added': 1,
            'source_checks': checks, 'tags': tags}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--today', default='2026-11-05')
    args = parser.parse_args()
    print(json.dumps(append(args.repo, args.source_dir, args.today)), flush=True)

if __name__ == '__main__':
    main()
