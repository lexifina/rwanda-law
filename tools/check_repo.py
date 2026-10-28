"""Checks the built repository against the official texts (the cached Gazette PDFs; offline).

    python -X utf8 check_repo.py [--repo DIR] [--record]

1. Every law commit's folder equals, file for file and byte for byte, the version built from the official texts:
   the extraction of the text itself (Constitution 2015 and 2023, the 2020 law as enacted), or the replay of the
   amending laws onto it.
2. Word check, independent of the structure parser: the words of each source text's English body column (in reading
   order) equal the words of its paragraphs joined with spaces only at block boundaries; and, for the whole-text
   versions, the words of the committed files (headings and paragraphs in article order, chapter lines where they
   first appear) equal the column's words.
3. Each amending law: every paragraph it restates appears, line for line, in the file it names in that commit; files
   it does not name are byte-identical to the previous commit.
4. Each commit's In-force trailer equals the Gazette date read from the running heads, and its author is the law.
Blobs are read through `git ls-tree` + `git cat-file --batch`.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402


def blobs(repo, commit, folder):
    names = [n for n in subprocess.run(['git', 'ls-tree', '-r', '--name-only', commit, folder + '/'], cwd=repo,
                                       capture_output=True, text=True, encoding='utf-8').stdout.split('\n') if n]
    p = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo, input=''.join(f'{commit}:{n}\n' for n in names).encode(),
                       capture_output=True)
    out, buf, i = {}, p.stdout, 0
    for n in names:
        j = buf.index(b'\n', i)
        size = int(buf[i:j].split()[2])
        out[n.split('/', 1)[1]] = buf[j + 1:j + 1 + size].decode('utf-8')
        i = j + 1 + size + 1
    return out


def file_words(files: dict) -> list:
    """Words of a whole-text version as the column prints them: enacting formula, preamble, then per article the
    chapter/section/subsection headings where they change, the heading and the paragraphs."""
    out = files.get('enacting-formula.md', '').split() + files.get('preamble.md', '').split()
    ctx = {'Chapter': '', 'Section': '', 'Subsection': ''}
    arts = sorted(n for n in files if n.startswith('art-'))
    for n in arts:
        lines = files[n].split('\n')
        head, rest = lines[0][2:], lines[1:]
        new_ctx = dict(ctx, Section=ctx['Section'], Subsection=ctx['Subsection'])
        given = {}
        while rest and rest[0]:
            k, _, v = rest[0].partition(': ')
            given[k] = v
            rest = rest[1:]
        new_ctx = {k: given.get(k, '') for k in ctx}
        for k in ('Chapter', 'Section', 'Subsection'):
            if new_ctx[k] and new_ctx[k] != ctx[k]:
                out += new_ctx[k].split()
        ctx = new_ctx
        out += head.split()
        for line in rest:
            out += line.split()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(HERE.parents[2] / 'rwanda-law'))
    ap.add_argument('--record', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    repo = a.repo
    evs = B.events(offline=True)
    log = subprocess.run(['git', 'log', '--reverse', '--first-parent',
                          '--format=%H%x09%an%x09%(trailers:key=In-force,valueonly,separator=)', 'main'],
                         cwd=repo, capture_output=True, text=True, encoding='utf-8').stdout.splitlines()
    law = [l.split('\t') for l in log if l.split('\t')[1] != 'Lexifina']
    problems = []
    if len(law) != len(evs):
        problems.append(f'{len(law)} law commits, {len(evs)} expected')
    files_checked = 0
    prev = {}
    for (h, au, day), (eday, _o, folder, files, author, _e, _m, tag) in zip(law, evs):
        # 4
        if au != author or day.strip() != eday:
            problems.append(f'{tag}: author/date {au} {day} != {author} {eday}')
        # 1
        got = blobs(repo, h, folder)
        for n in sorted(set(got) | set(files)):
            files_checked += 1
            if got.get(n) != files.get(n):
                problems.append(f'{tag}: {folder}/{n} differs from the official text')
        # 3
        if folder == 'law-2020-017' and prev.get(folder) is not None and not tag.endswith('2020-017'):
            am = next(x for x in B.STATUTE['amendments'] if f'{folder}/{x["tag"]}' == tag)
            st = B.load(am['file'], True)
            state = B.state_of(B.load(B.STATUTE['base']['file'], True))
            for x in B.STATUTE['amendments']:
                ops = B.apply_law(state, B.load(x['file'], True))
                if x is am:
                    break
            named = {B.fname(k) for _, k, _ in ops}
            for op, k, new in ops:
                lines = got.get(B.fname(k), '').split('\n')
                for p in new:
                    if op != 'repealed' and p not in lines and '# ' + p not in lines:
                        problems.append(f'{tag}: restated paragraph not in {B.fname(k)}: {p[:50]}')
                if op == 'repealed' and B.fname(k) in got:
                    problems.append(f'{tag}: repealed {B.fname(k)} still present')
            for n in set(got) | set(prev[folder]):
                if n not in named and got.get(n) != prev[folder].get(n):
                    problems.append(f'{tag}: {n} changed but not named by the law')
            del st
        prev[folder] = got
    # 2
    words = []
    for fid in [v['file'] for v in B.CONSTITUTION['versions']] + [B.STATUTE['base']['file']] + \
               [x['file'] for x in B.STATUTE['amendments']]:
        st = B.load(fid, True)
        flat = [w for p in __import__('extract').flatten(st) for w in p.split()]
        ok = flat == st['body_words']
        words.append(f'{fid}:{"equal" if ok else "DIFFERENT"}')
        if not ok:
            problems.append(f'word check (paragraphs vs column) failed for file {fid}')
    for (h, au, day), e in zip(law, evs):
        tag = e[7]
        if tag in ('constitution/2015', 'constitution/2023', 'law-2020-017/2020-017'):
            fid = {'constitution/2015': 5144, 'constitution/2023': 3939, 'law-2020-017/2020-017': 4423}[tag]
            st = B.load(fid, True)
            fw = [w for w in file_words(blobs(repo, h, e[2]))]
            ok = fw == st['body_words']
            words.append(f'{tag} files:{"equal" if ok else "DIFFERENT"}')
            if not ok:
                problems.append(f'word check (files vs column) failed for {tag}')
    summary = (f'{len(law)} law commits; {files_checked} file comparisons against the official texts; word checks '
               f'{", ".join(words)}; {len(problems)} problems')
    print(summary)
    for p in problems:
        print('PROBLEM', p)
    if a.record:
        vp = HERE / 'verification.json'
        rec = json.loads(vp.read_text(encoding='utf-8')) if vp.exists() else {}
        rec['check'] = {'summary': summary, 'problems': problems}
        vp.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(1 if problems else 0)


if __name__ == '__main__':
    main()
