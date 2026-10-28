"""Builds the Rwandan git-for-law repository from the Rwanda Law Reform Commission's open API (amategeko.gov.rw).

    python -X utf8 build.py [--repo DIR] [--offline] [--today YYYY-MM-DD] [--verify-rebuild]

Two acts, English text only (the English column of the trilingual Official Gazette, extract.py):
  constitution/    The Constitution of 2003 revised in 2015 (the record starts here: the 2003 original and its
                   2003-2010 amendments are served only as scans without a text layer), then the 2023 revising act,
                   which restates the whole Constitution: a labelled whole-text replacement.
  law-2020-017/    Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants, and the
                   three amending laws 019/2020, 052/2024 and 017/2026, REPLAYED (replay below): each amending article
                   restates the whole new text of the article it inserts or amends, or repeals it. No AI, no fuzzy
                   edits; anything the grammar does not recognise stops the build.
In-force dates: each text's own final article ("comes into force on the date of its publication in the Official
Gazette", or "upon promulgation ... and its publication in the Official Gazette") read together with the Gazette's
running head ("Official Gazette n° Special of DD/MM/YYYY"); both are quoted in an Evidence: trailer.
Commits at noon Kigali (CAT, UTC+2, no summer time). Needs PyMuPDF.
"""
import argparse
import collections
import datetime as dt
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract as X  # noqa: E402
import source as S  # noqa: E402

COMMITTER = ('Lexifina', 'rwanda-law@lexifina.com')
API_FILE = 'https://apis.amategeko.gov.rw/v1/site/documents-files/'

CONSTITUTION = {
    'dir': 'constitution', 'short': 'Constitution',
    'name': 'The Constitution of the Republic of Rwanda',
    'versions': [
        {'file': 5144, 'tag': '2015', 'author': 'Constitution of 2003 revised in 2015',
         'email': 'og-special-2015-12-24@amategeko.invalid', 'commence': 177,
         'title': 'The Constitution of the Republic of Rwanda of 2003 revised in 2015'},
        {'file': 3939, 'tag': '2023', 'author': 'Revision of 2023 of the Constitution',
         'email': 'og-special-2023-08-04@amategeko.invalid', 'commence': 176,
         'title': 'Revision of the Constitution of the Republic of Rwanda of 2003 revised in 2015 (2023)'},
    ]}
STATUTE = {
    'dir': 'law-2020-017', 'short': 'Public servants statute', 'ident': 'Law n° 017/2020',
    'name': 'Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants',
    'base': {'file': 4423, 'tag': '2020-017', 'author': 'Law n° 017/2020', 'email': 'law-2020-017@amategeko.invalid'},
    'amendments': [
        {'file': 4193, 'tag': '2020-019', 'author': 'Law n° 019/2020', 'email': 'law-2020-019@amategeko.invalid'},
        {'file': 6109, 'tag': '2024-052', 'author': 'Law n° 052/2024', 'email': 'law-2024-052@amategeko.invalid'},
        {'file': 11115, 'tag': '2026-017', 'author': 'Law n° 017/2026', 'email': 'law-2026-017@amategeko.invalid'},
    ]}

GAZETTE = re.compile(r'Official Gazette n° Special of (\d\d)/(\d\d)/(\d{4})')
COMMENCE = re.compile(r'comes into force (?:on the date of its publication|upon promulgation by the President of the '
                      r'Republic and its publication) in the Official Gazette of the Republic of Rwanda')
TAKES_EFFECT = re.compile(r'It takes effects? as of (\d{1,2}) (\w+) (\d{4})')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
          'December']
KIGALI = re.compile(r'^Kigali, on (\d\d)/(\d\d)/(\d{4})$')


class ReplayError(Exception):
    pass


# ---- reading a text ---------------------------------------------------------------------------------------------------
_DOCS = {}


def load(file_id: int, offline: bool) -> dict:
    if file_id in _DOCS:
        return _DOCS[file_id]
    import pymupdf
    meta = S.meta(file_id, offline)
    path = S.pdf_path(file_id, offline)
    doc = pymupdf.open(str(path))
    st = X.structure(doc)
    heads = collections.Counter(m.groups() for p in doc for m in GAZETTE.finditer(p.get_text()))
    if len(heads) != 1:
        raise SystemExit(f'file {file_id}: running heads name {len(heads)} Gazette dates: {heads}')
    d, m, y = next(iter(heads))
    st['gazette'] = f'{y}-{m}-{d}'
    st['gazette_printed'] = f'Official Gazette n° Special of {d}/{m}/{y}'
    st['meta'] = meta
    st['file'] = file_id
    st['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    _DOCS[file_id] = st
    return st


def articles(st: dict) -> list:
    return [it for k, it in st['items'] if k == 'article']


def in_force(st: dict, art_no: int = None) -> dict:
    """The day from the text's final (or named) article and the Gazette head; raises if the wording is not the one
    the rule reads."""
    arts = articles(st)
    a = arts[-1] if art_no is None else next(x for x in arts if x['key'] == art_no)
    text = ' '.join(a['paras'])
    if not COMMENCE.search(text):
        raise SystemExit(f'file {st["file"]}: Article {a["num"]} does not have the declared commencement wording: {text}')
    out = {'day': st['gazette'], 'article': a, 'quote': text,
           'evidence': f'Article {a["num"]} ({a["heading"]}): "{text}"; published in {st["gazette_printed"]}'}
    m = TAKES_EFFECT.search(text)
    if m:
        out['takes_effect'] = f'{m.group(3)}-{MONTHS.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}'
    for s in st['signature']:
        k = KIGALI.match(s)
        if k:
            out['promulgated'] = f'{k.group(3)}-{k.group(2)}-{k.group(1)}'
    if out.get('promulgated', '') > out['day']:
        raise SystemExit(f'file {st["file"]}: promulgated after publication')
    return out


# ---- the article model --------------------------------------------------------------------------------------------------
def akey(num: str) -> tuple:
    m = re.fullmatch(r'(One|one|\d+)(?: (bis|ter|quater))?', num)
    if not m:
        raise ReplayError(f'bad article number {num!r}')
    return (1 if m.group(1) in ('One', 'one') else int(m.group(1)), ['', 'bis', 'ter', 'quater'].index(m.group(2) or ''))


def fname(k: tuple) -> str:
    return f'art-{k[0]:03d}' + ('', '-bis', '-ter', '-quater')[k[1]] + '.md'


def state_of(st: dict) -> dict:
    return {'enacting': list(st['enacting']), 'preamble': list(st['preamble']),
            'arts': {akey(a['num']): {'printed': a['printed'], 'chapter': a['chapter'], 'section': a['section'],
                                      'subsection': a['subsection'], 'paras': list(a['paras'])} for a in articles(st)}}


def render(a: dict) -> str:
    out = ['# ' + a['printed']]
    for k in ('chapter', 'section', 'subsection'):
        if a[k]:
            out.append(f'{k.capitalize()}: {a[k]}')
    out.append('')
    out += a['paras']
    return '\n'.join(out) + '\n'


def files_of(state: dict) -> dict:
    d = {'enacting-formula.md': '\n'.join(state['enacting']) + '\n'}
    if state['preamble']:
        d['preamble.md'] = '\n'.join(state['preamble']) + '\n'
    for k in sorted(state['arts']):
        d[fname(k)] = render(state['arts'][k])
    return d


# ---- replay of an amending law ------------------------------------------------------------------------------------------
BASE_REF = r'Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants'
OP_AMEND = re.compile(r'^Article (\d+(?: bis)?) of ' + BASE_REF + r' is (?:modified|amended) as follows:$')
OP_INSERT = re.compile(r'^In ' + BASE_REF + r', Article (\d+ bis) is inserted to read as follows:$')
OP_REPEAL = re.compile(r'^Article (\d+(?: bis)?) of ' + BASE_REF + r' is repealed\.$')
OWN = re.compile(r'^(This Law was drafted, considered and adopted in Ikinyarwanda\.|This Law comes into force )')
OPEN_Q = re.compile(r'^[«“"]\s*')
CLOSE_Q = re.compile(r'\s*[»”"](?=\.?$)')
QUOTED_HEAD = re.compile(r'^Article (\d+(?: bis)?): (.+)$')


def unquote(paras: list) -> list:
    """The restated text without the quotation marks around it (the opening mark on the first paragraph, the closing
    mark at the end of the last, before or after its full stop)."""
    if not paras or not OPEN_Q.match(paras[0]) or not CLOSE_Q.search(paras[-1]):
        raise ReplayError(f'restated text is not quoted: {paras[:1]} ... {paras[-1:]}')
    out = list(paras)
    out[0] = OPEN_Q.sub('', out[0])
    out[-1] = CLOSE_Q.sub('', out[-1])
    return out


def apply_law(state: dict, st: dict) -> list:
    """Replay one amending law onto state (in place). Returns [(op, key, quoted paragraphs)]."""
    ops = []
    for a in articles(st):
        lead, rest = a['paras'][0], a['paras'][1:]
        m = OP_AMEND.match(lead) or OP_INSERT.match(lead)
        if m:
            k = akey(m.group(1))
            new = unquote(rest)
            head = QUOTED_HEAD.match(new[0])
            if OP_INSERT.match(lead):
                if k in state['arts'] or not head or akey(head.group(1)) != k:
                    raise ReplayError(f'insertion of {m.group(1)}: already present or no heading')
                prev = state['arts'][max(x for x in state['arts'] if x < k)]
                state['arts'][k] = {'printed': new[0], 'chapter': prev['chapter'], 'section': prev['section'],
                                    'subsection': prev['subsection'], 'paras': new[1:]}
                ops.append(('inserted', k, new))
            else:
                if k not in state['arts']:
                    raise ReplayError(f'amendment of absent Article {m.group(1)}')
                old = state['arts'][k]
                if head:
                    if akey(head.group(1)) != k:
                        raise ReplayError(f'Article {m.group(1)} restated under another number')
                    old['printed'], old['paras'] = new[0], new[1:]
                else:
                    old['paras'] = new
                ops.append(('amended', k, new))
            continue
        m = OP_REPEAL.match(lead)
        if m and not rest:
            k = akey(m.group(1))
            if k not in state['arts']:
                raise ReplayError(f'repeal of absent Article {m.group(1)}')
            del state['arts'][k]
            ops.append(('repealed', k, []))
            continue
        if OWN.match(lead) and not rest:
            continue
        raise ReplayError(f'Article {a["num"]} of file {st["file"]} not understood: {lead[:120]}')
    return ops


def label(k: tuple) -> str:
    return f'Article {k[0]}' + ('', ' bis', ' ter', ' quater')[k[1]]


# ---- dates and git ------------------------------------------------------------------------------------------------------
def stamp(day: str, extra: int = 0) -> str:
    """Noon in Kigali: Central Africa Time, UTC+2 all year (no summer time)."""
    dt.date.fromisoformat(day)
    return f'{day}T12:00:{extra:02d}+0200'


def git(repo, *args, env=None, inp=None):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', *args], cwd=repo, env=e,
                       input=inp, capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        raise SystemExit(f'git {" ".join(args)}: {r.stderr}')
    return r.stdout


def commit(repo, author, email, day, msg, extra=0):
    ts = stamp(day, extra)
    env = {'GIT_AUTHOR_NAME': author, 'GIT_AUTHOR_EMAIL': email, 'GIT_AUTHOR_DATE': ts,
           'GIT_COMMITTER_NAME': COMMITTER[0], 'GIT_COMMITTER_EMAIL': COMMITTER[1], 'GIT_COMMITTER_DATE': ts}
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '--allow-empty', '-F', '-', env=env, inp=msg)


def rmtree(p):
    def fix(func, path, exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(p, onexc=fix)


def sync(repo: Path, folder: str, files: dict):
    d = repo / folder
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name in sorted(files):
        (d / name).write_text(files[name], encoding='utf-8', newline='\n')


def trailers(pairs: list) -> str:
    return '\n'.join(f'{k}: {v}' for k, v in pairs if v)


# ---- the events ---------------------------------------------------------------------------------------------------------
def events(offline: bool) -> list:
    """[(day, order, folder, files, author, email, message, tag)] in in-force order."""
    out = []
    # Constitution
    c = CONSTITUTION
    prev_files = None
    for i, v in enumerate(c['versions']):
        st = load(v['file'], offline)
        inf = in_force(st, v['commence'])
        files = files_of(state_of(st))
        meta = st['meta']['document']
        if i == 0:
            subject = f'{c["short"]}: {v["title"]} (record starts here)'
            body = (f'{v["title"]}, {st["gazette_printed"]}: the whole text (English column).\n\n'
                    'Record starts here; 2003–2010 texts are scans without a text layer. The Constitution of '
                    '04/06/2003 and its amendments of 2003, 2005, 2008 and 2010 are on amategeko.gov.rw only as '
                    'scanned images (the 2003 original has no text layer at all; amendment no. 1 has only a '
                    'machine-read OCR layer), so no checkable text exists for them. The 2015 revision restates the '
                    'whole Constitution, so the record begins with it.')
            kind = 'revision (whole text; record starts here)'
            affecting = []
        else:
            subject = f'{c["short"]}: replacement by the revision of 2023 (whole text)'
            changed = sorted(n for n in set(files) | set(prev_files) if files.get(n) != prev_files.get(n))
            body = (f'{v["title"]}, {st["gazette_printed"]}.\n\n'
                    'Replacement. The 2023 revising act restates and renumbers the whole Constitution '
                    f'({len(articles(st))} articles, against {len(prev_files) - 2} in 2015). Every file is replaced by '
                    'the new text; the changes are not attributed article by article, and an article file of the '
                    'same number may hold a different provision after this commit. '
                    f'{len(changed)} files differ (listed in Affecting:).')
            kind = 'replacement'
            affecting = [f'{c["dir"]}/{n}' for n in changed]
        msg = subject + '\n\n' + body + '\n\n' + trailers(
            [('Kind', kind), ('Evidence', inf['evidence']), ('Promulgated', inf.get('promulgated')),
             ('Published', f'{st["gazette"]} ({st["gazette_printed"]})'), ('In-force', inf['day'])]
            + [('Affecting', a) for a in affecting]
            + [('Source', API_FILE + str(v['file'])), ('Source-file', meta['name']),
               ('Source-sha256', st['sha256'])]) + '\n'
        out.append((inf['day'], 0, c['dir'], files, v['author'], v['email'], msg, f'{c["dir"]}/{v["tag"]}'))
        prev_files = files
    # Statute
    s = STATUTE
    st = load(s['base']['file'], offline)
    inf = in_force(st)
    state = state_of(st)
    files = files_of(state)
    msg = (f'{s["short"]}: {s["name"]}\n\nThe law as enacted and published in {st["gazette_printed"]} (English '
           'column): the base of the replay.\n\n' + trailers(
               [('Kind', 'Law'), ('Evidence', inf['evidence']), ('Published', f'{st["gazette"]} ({st["gazette_printed"]})'),
                ('In-force', inf['day'])]
               + [('Source', API_FILE + str(s['base']['file'])), ('Source-sha256', st['sha256'])]) + '\n')
    out.append((inf['day'], 1, s['dir'], files, s['base']['author'], s['base']['email'], msg, f'{s["dir"]}/{s["base"]["tag"]}'))
    for am in s['amendments']:
        st = load(am['file'], offline)
        inf = in_force(st)
        ops = apply_law(state, st)
        files = files_of(state)
        title = st['enacting'][0]
        what = collections.defaultdict(list)
        for op, k, _ in ops:
            what[op].append(label(k))
        subject = f'{s["short"]}: ' + ', '.join(label(k) for _, k, _ in ops) + f' ({am["author"]})'
        body = (f'{title}, {st["gazette_printed"]}.\n\nReplayed: each article of this law restates the whole new text '
                'of the article it amends or inserts, or repeals it; the text below is that restated text, applied '
                'as printed. No official consolidation of Law n° 017/2020 is published, so the result is not checked '
                'against one.')
        if 'takes_effect' in inf:
            body += (f'\n\nThe law also states that it "takes effects as of" {inf["takes_effect"]}, before its '
                     'publication; the commit is dated by entry into force, and Takes-effect: records the earlier day.')
        if any(op == 'amended' and not QUOTED_HEAD.match(new[0]) for op, _, new in ops):
            body += ('\n\nWhere the amending article restates only the body of an article, its heading is kept as '
                     'enacted (the amending law\'s own article heading is not part of the restated text).')
        msg = subject + '\n\n' + body + '\n\n' + trailers(
            [('Kind', 'Law (amending)')]
            + [(op.capitalize(), lab) for op in ('amended', 'inserted', 'repealed') for lab in what.get(op, [])]
            + [('Evidence', inf['evidence']), ('Published', f'{st["gazette"]} ({st["gazette_printed"]})'),
               ('In-force', inf['day']), ('Takes-effect', inf.get('takes_effect'))]
            + [('Affecting', f'{s["ident"]}, {label(k)}') for _, k, _ in ops]
            + [('Source', API_FILE + str(am['file'])), ('Source-sha256', st['sha256'])]) + '\n'
        out.append((inf['day'], 1, s['dir'], files, am['author'], am['email'], msg, f'{s["dir"]}/{am["tag"]}'))
    out.sort(key=lambda e: (e[0], e[1]))
    return out


def build(repo: Path, offline: bool, today: str):
    evs = events(offline)
    if repo.exists():
        for p in repo.iterdir():
            if p.name != '.git':
                rmtree(p) if p.is_dir() else p.unlink()
    else:
        repo.mkdir(parents=True)
    remote = None
    if (repo / '.git').exists():
        r = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=repo, capture_output=True, text=True)
        remote = r.stdout.strip() or None
        rmtree(repo / '.git')
    git(repo, 'init', '-q', '-b', 'main')
    if remote:
        git(repo, 'remote', 'add', 'origin', remote)
    (repo / '.gitattributes').write_text('* text eol=lf\n', encoding='utf-8', newline='\n')
    for n, (day, _o, folder, files, author, email, msg, tag) in enumerate(evs):
        sync(repo, folder, files)
        commit(repo, author, email, day, msg, extra=n)
        git(repo, 'tag', tag)
    import reproduce
    reproduce.write_docs(repo, evs, today, HERE)
    git(repo, 'add', '-A')
    ts = stamp(today)
    env = {'GIT_AUTHOR_NAME': COMMITTER[0], 'GIT_AUTHOR_EMAIL': COMMITTER[1], 'GIT_AUTHOR_DATE': ts,
           'GIT_COMMITTER_NAME': COMMITTER[0], 'GIT_COMMITTER_EMAIL': COMMITTER[1], 'GIT_COMMITTER_DATE': ts}
    git(repo, 'commit', '-q', '-F', '-', env=env,
        inp=('Documentation, tools and REPRODUCE.md\n\nNo law text changes: README, LICENSE, corpus.json, tools and '
             'REPRODUCE.md.\n\nKind: documentation\nIn-force: ' + today + '\n'))
    return git(repo, 'rev-parse', 'HEAD').strip(), len(evs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(HERE.parents[2] / 'rwanda-law'))
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--today', default=None, help='documentation commit day (default: the cache retrieval day)')
    ap.add_argument('--verify-rebuild', action='store_true', help='rebuild into a temporary folder and compare hashes')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    today = a.today or S.retrieved()
    if a.verify_rebuild:
        tmp = HERE / 'cache' / 'rebuild'
        if tmp.exists():
            rmtree(tmp)
        h, _ = build(tmp, True, today)
        main_h = git(Path(a.repo), 'rev-parse', 'main').strip()
        print('rebuild', h, 'repo', main_h, 'IDENTICAL' if h == main_h else 'DIFFERENT')
        rmtree(tmp)
        raise SystemExit(0 if h == main_h else 1)
    h, n = build(Path(a.repo), a.offline, today)
    print('law commits:', n, 'main', h)


if __name__ == '__main__':
    main()
