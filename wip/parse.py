"""Reads only .cache/ and writes corpus.json (scripts/gitlaw_common/SCHEMA.md) for Rwanda. Deterministic.

    python -X utf8 parse.py

Texts: the English column of the trilingual Official Gazette PDFs served by the Rwanda Law Reform Commission's API
(amategeko.gov.rw), read by extract.py from the PDF text layer (no OCR anywhere). Court rulings: the English text of
the Rwanda Law Reports (RLR) volumes on the same API.

Acts
  constitution/     The Constitution of 2003 revised in 2015 (Official Gazette n° Special of 24/12/2015), then the 2023
                    revision (Official Gazette n° Special of 04/08/2023), which restates the whole Constitution.
  penal-code/       Law n° 68/2018 of 30/08/2018 determining offences and penalties in general, with
                      - Re Mugisha, Supreme Court, 24 April 2019 (RLR V.3-2019): Art. 136 para. 3 reframed, paras. 4-5
                        of no effect, Arts. 154 and 233 repealed;
                      - Law n° 69/2019 of 08/11/2019 (replayed);
                      - Re Byansi, Supreme Court, 20 May 2022 (RLR V.4-2022): Art. 218 devoid of effects;
                      - Law n° 059/2023 of 04/12/2023 (replayed).
  data-protection/  Law n° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy (unamended).

Replay grammar (anything else stops the parse): an amending article's first paragraph is one of
  "Article N of [the] Law n° 68/2018 of 30/08/2018 determining offences and penalties [in general] is amended as follows:"
  "Article N of [the] Law n° 68/2018 ... is repealed."
  "In Law n° 68/2018 ... an Article N bis is inserted which is worded as follows:"
and its other paragraphs are the quoted new text. Their opening quote (at the start of the first paragraph, or after its
"(1) ") and closing quote (at the end of the last) are removed. When the quoted text begins with "Article N: heading",
that line replaces the heading; otherwise the article keeps its heading (decisions). The amending law's own language,
general-repeal and commencement articles are recognised and skipped.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract as X  # noqa: E402
import fetch as F  # noqa: E402

API = F.API
ACTS = json.loads((HERE / 'acts.json').read_text(encoding='utf-8'))
_META = {}


def meta(fid: int) -> dict:
    if fid not in _META:
        p = F.meta_path(fid)
        if not p.exists():
            raise SystemExit(f'file {fid} is not in the cache: run fetch.py')
        _META[fid] = json.loads(p.read_text(encoding='utf-8'))
    return _META[fid]


def pdf(fid: int):
    m = meta(fid)
    b = F.pdf_path(m).read_bytes()
    assert hashlib.sha256(b).hexdigest() == m['pdf_sha256'], fid
    return pymupdf.open(stream=b, filetype='pdf'), m['pdf_sha256']


# ---- typesetting, normalised once -----------------------------------------------------------------------------------
def norm(s: str) -> str:
    s = s.replace(' ', ' ').replace('­', '').replace('​', '')
    s = re.sub(r'(?<=\w)‟(?=\w)', "'", s)
    s = re.sub(r'«\s*', '"', s)
    s = re.sub(r'\s*»', '"', s)
    s = re.sub('[“”„‟″]', '"', s)
    s = re.sub('[‘’‚′`]', "'", s)
    s = s.replace('—', '–')
    s = re.sub(r'\b([Nn])\s*[º°]\s*(?=\d)', r'\1° ', s)       # "Nº68/2018", "n°68" -> "N° 68"
    s = re.sub(r'\b([Nn])[º°]', r'\1°', s)
    s = re.sub(r'(?<=\d) ?[º°˚](?=\s)', '°', s)               # "1 º " list ordinals -> "1° "
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def art_key(num: str, suffix: str = '') -> str:
    n = 1 if num.lower() == 'one' else int(num)
    return f'art-{n:03d}' + (f'-{suffix}' if suffix else '')


def art_label(key: str) -> str:
    m = re.match(r'art-(\d+)(?:-(\w+))?$', key)
    return f'Article {int(m.group(1))}' + (f' {m.group(2)}' if m.group(2) else '')


def text_of(lines: list) -> str:
    return '\n'.join(norm(l) for l in lines) + '\n'


def read_whole(fid: int, preamble: bool = False) -> tuple[dict, str, dict]:
    doc, sha = pdf(fid)
    st = X.structure(doc)
    units = {}
    if preamble and st['preamble']:
        units['preamble'] = {'label': 'Preamble', 'kind': 'preamble', 'text': text_of(st['preamble'])}
    for kind, it in st['items']:
        if kind != 'article':
            continue
        k = art_key(str(it['key']))
        units[k] = {'label': art_label(k), 'kind': 'art', 'text': text_of([it['printed']] + it['paras'])}
    return units, sha, st


# ---- the amending laws ------------------------------------------------------------------------------------------------
LAW68 = r'(?:the )?Law n° ?68/2018 of 30/08/2018 determining offences and penalties(?: in general)?'
AMEND = re.compile(rf'^Article (\d+) of {LAW68} is amended as follows:$')
REPEAL = re.compile(rf'^Article (\d+) of {LAW68} is repealed\.$')
INSERT = re.compile(rf'^In {LAW68},? an Article (\d+) (bis|ter) is inserted which is worded as follows:$')
SKIP = re.compile(r'^(This Law was drafted, considered and adopted in Ikinyarwanda\.|All prior legal provisions contrary '
                  r'to this Law are repealed\.|This Law comes into force on the date of its publication in the Official '
                  r'Gazette of the Republic of Rwanda\.)$')
UNCLOSED = []
RESTATED_HEAD = re.compile(r'^Article (\d+)(?: (bis|ter))?\s*:\s*(.+)$')


def unquote(paras: list) -> list:
    ps = list(paras)
    m = re.match(r'^(\(\d+\) )?"\s*', ps[0])
    if not m:
        raise SystemExit('restated text without an opening quote: ' + ps[0][:80])
    ps[0] = (m.group(1) or '') + ps[0][m.end():]
    if not ps[-1].endswith('"'):
        UNCLOSED.append(ps[0][:60])   # the Gazette omits the closing mark; the article ends here anyway
        return ps
    ps[-1] = ps[-1][:-1].rstrip()
    return ps


def replay(fid: int, prev: dict) -> tuple[dict, list, str]:
    """(changes, ops, sha256): the changes an amending law makes to prev's units."""
    doc, sha = pdf(fid)
    st = X.structure(doc)
    changes, ops = {}, []
    for kind, it in st['items']:
        if kind != 'article':
            continue
        paras = [norm(p) for p in it['paras']]
        first, rest = paras[0], paras[1:]
        if SKIP.match(first) and not rest:
            continue
        m_a, m_r, m_i = AMEND.match(first), REPEAL.match(first), INSERT.match(first)
        if m_r and not rest:
            k = art_key(m_r.group(1))
            if k in prev:
                changes[k] = None
                ops.append(('repealed', k, it['key']))
            else:
                ops.append(('repealed-already-absent', k, it['key']))
            continue
        if m_a or m_i:
            k = art_key(m_a.group(1)) if m_a else art_key(m_i.group(1), m_i.group(2))
            new = unquote(rest)
            head = RESTATED_HEAD.match(new[0])
            if head:
                if art_key(head.group(1), head.group(2) or '') != k:
                    raise SystemExit(f'file {fid} art {it["key"]}: restated heading {new[0][:60]} is not {k}')
                lines = new
            elif m_a:
                if k not in prev:
                    raise SystemExit(f'file {fid} art {it["key"]}: amends absent {k}')
                lines = [prev[k]['text'].split('\n', 1)[0]] + new
            else:
                raise SystemExit(f'file {fid} art {it["key"]}: inserted article without a heading')
            if m_i and k in prev:
                raise SystemExit(f'file {fid}: inserts {k}, which exists')
            changes[k] = {'label': art_label(k), 'kind': 'art', 'text': text_of(lines)}
            ops.append(('inserted' if m_i else 'amended', k, it['key']))
            continue
        raise SystemExit(f'file {fid} art {it["key"]}: not in the replay grammar: {first[:120]}')
    return changes, ops, sha


# ---- the court rulings (Rwanda Law Reports, English text) -----------------------------------------------------------
def rlr_text(fid: int, first: int, last: int) -> str:
    doc, _ = pdf(fid)
    t = ' '.join(doc[i].get_text() for i in range(first - 1, last))
    t = re.sub(r'\s+', ' ', t)
    return t


def mugisha() -> tuple[str, dict, str]:
    """RLR V.3-2019 (file 6410), English report of Re Mugisha, pp. 292-293 of the PDF: the Court's declarations."""
    fid = 6410
    t = rlr_text(fid, 292, 293)
    t = t.replace(' Re MUGISHA RWANDA LAW REPORTS 64 ', ' ')       # the running heads at the page break
    for need in ['[133] Declares that paragraphs 4 and 5 of Article 136 of Law No 68/2018 of 30/08/2018 determining '
                 'offences and penalties in general are invalid and of no effect.',
                 '[135] Declares that Article 154 of Law No 68/2018 of 30/08/2018 determining offences and penalties in '
                 'general is contrary to Article 38 of the Constitution and thus is hereby repealed.',
                 '[136] Declares that Article 233 of Law No 68/2018 of 30/08/2018 determining offences and penalties in '
                 'general is contrary to Articles 15 and 38 of the Constitution. This Article is hereby repealed.']:
        if need not in t:
            raise SystemExit('Re Mugisha: declaration not found: ' + need[:60])
    m = re.search(r'\[132\] Declares that paragraph 3 of Article 136 is hereby reframed in the following manner: '
                  r'[“"](.+?)[”"] \[133\]', t)
    if not m:
        raise SystemExit('Re Mugisha: the reframed paragraph 3 of Article 136 was not found')
    return norm(m.group(1)), {'pages': '292-293'}, meta(fid)['pdf_sha256']


def byansi() -> str:
    """RLR V.4-2022 report of Re Byansi (Fond) (file 8624): the Court ruling."""
    fid = 8624
    doc, _ = pdf(fid)
    t = re.sub(r'\s+', ' ', ' '.join(p.get_text() for p in doc))
    need = ('Holds that article 218 of the Law nº 68/2018 of 30/08/2018 determining offences and penalties in general is '
            'contrary to article 38 of the Constitution, and is therefore devoid of effects;')
    if need not in t:
        raise SystemExit('Re Byansi: ruling on article 218 not found')
    if 'RS/INCONST/SPEC 00002/2021/SC' not in t or 'May 20, 2022]' not in t[:400]:
        raise SystemExit('Re Byansi: case number or date not found in the headnote')
    return meta(fid)['pdf_sha256']


# ---- building the corpus ----------------------------------------------------------------------------------------------
def gazette_day(fid: int) -> str:
    doc, _ = pdf(fid)
    days = set()
    for p in doc:
        for d, mth, y in re.findall(r'Official Gazette n(?:°|o\.) Special of (\d\d)/(\d\d)/(\d{4})', p.get_text()):
            days.add(f'{y}-{mth}-{d}')
    if len(days) != 1:
        raise SystemExit(f'file {fid}: running heads give {sorted(days)}')
    day = days.pop()
    if meta(fid)['document']['date'] != day:
        raise SystemExit(f'file {fid}: running head {day} differs from the portal date {meta(fid)["document"]["date"]}')
    return day


COMMENCE = re.compile(r'(comes into force on the date of its publication|comes into force upon promulgation by the '
                      r'President of the Republic and its publication) in the Official Gazette of the Republic of Rwanda')


def check_commencement(st: dict, fid: int) -> str:
    arts = [it for k, it in st['items'] if k == 'article']
    last = ' '.join(norm(p) for p in arts[-1]['paras'])
    if not COMMENCE.search(last):
        raise SystemExit(f'file {fid}: last article is not a commencement on publication: {last[:120]}')
    return norm(arts[-1]['printed']) + ' ' + COMMENCE.search(last).group(0)


def src(fid: int) -> str:
    return API + str(fid)


def main():
    laws, acts, decisions = {}, [], []

    # Constitution
    c15, sha15, st15 = read_whole(5144, preamble=True)
    c23, sha23, st23 = read_whole(3939, preamble=True)
    d15, d23 = gazette_day(5144), gazette_day(3939)
    ev15, ev23 = check_commencement(st15, 5144), check_commencement(st23, 3939)
    laws['constitution-2015'] = {
        'label': 'Constitution of 2003 revised in 2015',
        'title': 'The Constitution of the Republic of Rwanda of 2003 revised in 2015, passed by referendum of 18/12/2015',
        'kind': 'referendum', 'enacted': '2015-12-24', 'published': d15, 'url': src(5144),
        'temporary_until': None, 'restores': None, 'note': None}
    laws['constitution-revision-2023'] = {
        'label': 'Revision of the Constitution (2023)',
        'title': 'Revision of the Constitution of the Republic of Rwanda of 2003 revised in 2015, adopted by the '
                 'Chamber of Deputies and the Senate meeting in Constituent Assembly on 05 July 2023',
        'kind': 'law', 'enacted': None, 'published': d23, 'url': src(3939),
        'temporary_until': None, 'restores': None, 'note': None}
    laws['constitution-2003'] = {
        'label': 'Constitution of 4 June 2003', 'title': 'The Constitution of the Republic of Rwanda of 04 June 2003',
        'kind': 'referendum', 'enacted': '2003-06-04', 'published': '2003-06-04', 'url': src(10837),
        'temporary_until': None, 'restores': None, 'note': None}
    changed23 = {k: (c23.get(k)) for k in sorted(set(c15) | set(c23)) if c15.get(k) != c23.get(k)}
    acts.append({
        'slug': 'constitution', 'short': 'Constitution',
        'title': 'The Constitution of the Republic of Rwanda',
        'url': src(3939), 'first_law': 'constitution-2015', 'earlier_laws': ['constitution-2003'],
        'versions': [
            {'from': d15, 'source_url': src(5144), 'sha256': sha15, 'units': c15, 'credits': {},
             'note': 'The 2015 revision restates the whole Constitution of 2003, so every line is credited to it, '
                     'including words unchanged since 2003. The 2003 text and its amendments of 2003, 2005, 2008 and '
                     '2010 are not in this record (see the README).'},
            {'from': d23, 'source_url': src(3939), 'sha256': sha23, 'changes': changed23,
             'credits': {k: ['constitution-revision-2023'] for k in changed23},
             'note': 'The 2023 revision restates the whole Constitution and renumbers it (177 articles become 176), so '
                     'a file art-NNN.md can hold a different provision after 2023. Files are keyed by the article '
                     'number as printed.'}]})
    decisions += [
        f'Constitution: in force {d15} ({ev15}; promulgated "Kigali, on 24/12/2015"; Gazette running head) and {d23} '
        f'({ev23}; Gazette running head "Official Gazette n° Special of 04/08/2023").',
        'Constitution: the 2023 revision is treated as one whole-text replacement credited to it, compared article '
        'number by article number with the 2015 text.',
        'Constitution: the record starts with the 2015 revision. The 2003 Constitution (file 10837) is an image-only scan '
        'with no text layer, and amendment no. 1 of 2003 (file 5149) carries only an OCR layer, so neither is used (no '
        'OCR). The amendments of 2005 (5131), 2008 (5132) and 2010 (11489) have text layers but cannot be replayed '
        'without the 2003 base text.',
    ]

    # Penal Code
    pc0, sha0, st0 = read_whole(4119)
    d18 = gazette_day(4119)
    ev18 = check_commencement(st0, 4119)
    laws['law-2018-068'] = {
        'label': 'Law n° 68/2018', 'title': 'Law n° 68/2018 of 30/08/2018 determining offences and penalties in general',
        'kind': 'law', 'enacted': '2018-08-30', 'published': d18, 'url': src(4119),
        'temporary_until': None, 'restores': None, 'note': None}
    versions = [{'from': d18, 'source_url': src(4119), 'sha256': sha0, 'units': pc0, 'credits': {}}]
    cur = dict(pc0)

    # Re Mugisha, 24 April 2019
    para3, _, sham = mugisha()
    lines136 = cur['art-136']['text'].rstrip('\n').split('\n')
    if len(lines136) != 6:
        raise SystemExit(f'Article 136 has {len(lines136) - 1} paragraphs, expected 5')
    new136 = lines136[:3] + [para3]
    ch = {'art-136': {'label': 'Article 136', 'kind': 'art', 'text': '\n'.join(new136) + '\n'},
          'art-154': None, 'art-233': None}
    laws['sc-2019-mugisha'] = {
        'label': 'Re Mugisha (Supreme Court, 2019)',
        'title': 'Re Mugisha, Supreme Court of Rwanda, RS/INCONST/SPEC 00002/2018/SC, judgment of 24 April 2019 '
                 '(Rwanda Law Reports V.3-2019)',
        'kind': 'court', 'enacted': '2019-04-24', 'published': '2019-07-26', 'url': src(6410),
        'temporary_until': None, 'restores': None, 'note': None}
    versions.append({'from': '2019-04-24', 'source_url': src(6410), 'sha256': sham, 'changes': ch,
                     'credits': {k: ['sc-2019-mugisha'] for k in ch},
                     'note': 'The Supreme Court reframed paragraph 3 of Article 136 and declared its paragraphs 4 and 5 '
                             'invalid and of no effect, and repealed Articles 154 and 233 as contrary to the '
                             'Constitution. It held Articles 136 (paragraphs 1-3), 138, 139 and 236 constitutional.'})
    for k, u in ch.items():
        cur.pop(k, None) if u is None else cur.__setitem__(k, u)

    def amending(fid, key, label, title, enacted, note_extra=''):
        nonlocal cur
        day = gazette_day(fid)
        ch, ops, sha = replay(fid, cur)
        doc, _ = pdf(fid)
        ev = check_commencement(X.structure(doc), fid)
        laws[key] = {'label': label, 'title': title, 'kind': 'law', 'enacted': enacted, 'published': day,
                     'url': src(fid), 'temporary_until': None, 'restores': None, 'note': None}
        absent = [k for op, k, _ in ops if op == 'repealed-already-absent']
        note = None
        if absent:
            note = (f'{label} also repeals {", ".join(art_label(k) for k in absent)}, which the Supreme Court had '
                    f'already struck out; no words change there.' + note_extra)
        v = {'from': day, 'source_url': src(fid), 'sha256': sha, 'changes': ch, 'credits': {k: [key] for k in ch}}
        if note:
            v['note'] = note
        versions.append(v)
        for k, u in ch.items():
            cur.pop(k, None) if u is None else cur.__setitem__(k, u)
        decisions.append(f'{label}: in force {day} ({ev}; Gazette running head). Replayed: '
                         + '; '.join(f'Art. {a} {op} {art_label(k)}' for op, k, a in ops) + '.')
        if UNCLOSED:
            decisions.append(f'{label}: the English text prints no closing quotation mark after the restated text '
                             f'beginning {"; ".join(repr(u) for u in UNCLOSED)}; it ends with its article.')
            UNCLOSED.clear()

    amending(4115, 'law-2019-069', 'Law n° 69/2019',
             'Law n° 69/2019 of 08/11/2019 amending Law n° 68/2018 of 30/08/2018 determining offences and penalties in '
             'general', '2019-11-08')

    # Re Byansi, 20 May 2022
    shab = byansi()
    laws['sc-2022-byansi'] = {
        'label': 'Re Byansi (Supreme Court, 2022)',
        'title': 'Re Byansi (Fond), Supreme Court of Rwanda, RS/INCONST/SPEC 00002/2021/SC, judgment of 20 May 2022 '
                 '(Rwanda Law Reports V.4-2022)',
        'kind': 'court', 'enacted': '2022-05-20', 'published': None, 'url': src(8624),
        'temporary_until': None, 'restores': None, 'note': None}
    versions.append({'from': '2022-05-20', 'source_url': src(8624), 'sha256': shab, 'changes': {'art-218': None},
                     'credits': {'art-218': ['sc-2022-byansi']},
                     'note': 'The Supreme Court held Article 218 contrary to Article 38 of the Constitution and devoid '
                             'of effects. It held Articles 156, 157, 194 and 251 constitutional.'})
    cur.pop('art-218')

    amending(4073, 'law-2023-059', 'Law n° 059/2023',
             'Law n° 059/2023 of 04/12/2023 amending Law n° 68/2018 of 30/08/2018 determining offences and penalties in '
             'general', '2023-12-04')
    acts.append({'slug': 'penal-code', 'short': 'Penal Code',
                 'title': 'Law n° 68/2018 of 30/08/2018 determining offences and penalties in general',
                 'url': src(4119), 'first_law': 'law-2018-068', 'earlier_laws': [], 'versions': versions})
    decisions += [
        f'Penal Code: in force {d18} ({ev18}; Gazette running head "Official Gazette no. Special of 27/09/2018").',
        'Penal Code: no official consolidation exists (the portal serves the 2018 law and its two amending laws as '
        'separate Gazette texts), so the later versions are replays of the amending laws and of the two Supreme Court '
        'rulings. Each restated article is the amending law\'s own text, verbatim after normalisation.',
        'Penal Code: where an amending law restates only the body of an article, the article keeps the heading it had '
        '(Law 69/2019 Arts. 2-11 and Law 059/2023 Arts. 1-7, 9-11, 14, 15, 21 each carry a heading of their own, which '
        'is the amending article\'s heading, not a restated one).',
        'Court rulings: dated by the judgment day printed in the Rwanda Law Reports headnote (Re Mugisha "24 April 2019", '
        'Re Byansi "May 20, 2022"); each ruling ordered publication in the Official Gazette, which was not located, so '
        'the version takes effect on the judgment day. Struck or repealed articles are removed; Article 136 keeps '
        'paragraphs 1-2 and the Court\'s reframed paragraph 3 (RLR V.3-2019, English text, para. [132]).',
        'Penal Code: the 2018 table of contents misprints "Article 2826" for Article 286; the body is read from the '
        'second "Article One".',
    ]

    # Data protection
    dp, shad, std = read_whole(4116)
    d21 = gazette_day(4116)
    ev21 = check_commencement(std, 4116)
    laws['law-2021-058'] = {
        'label': 'Law n° 058/2021',
        'title': 'Law n° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy',
        'kind': 'law', 'enacted': '2021-10-13', 'published': d21, 'url': src(4116),
        'temporary_until': None, 'restores': None, 'note': None}
    acts.append({'slug': 'data-protection', 'short': 'Data Protection Law',
                 'title': 'Law n° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy',
                 'url': src(4116), 'first_law': 'law-2021-058', 'earlier_laws': [],
                 'versions': [{'from': d21, 'source_url': src(4116), 'sha256': shad, 'units': dp, 'credits': {}}]})
    decisions += [
        f'Data protection: in force {d21} ({ev21}; Gazette running head). The portal lists no amending law. Article 67 '
        'gives controllers and processors already in operation two years from publication to conform; this is left in '
        'the text and not encoded in applies.',
        'Text: the English column only (extract.py: running heads removed by content, columns from the two gutters, '
        'paragraphs by line pitch). Normalised once: NBSP and soft hyphens, one form of quotes and apostrophes ("\'), '
        'em dash to en dash, "Nº"/"n°" to "N°"/"n°", list ordinals "1 º" to "1°". Each file is "Article N: heading" '
        'as printed, then one paragraph per line.',
        'Every text has a PDF text layer (checked with PyMuPDF); no OCR is used anywhere.',
        'Sources: the API metadata and the PDFs; robots.txt of amategeko.gov.rw allows all agents. No Wayback capture '
        'was needed.',
    ]

    retrieved = sorted({meta(f)['retrieved'] for f in (5144, 3939, 4119, 4115, 4073, 4116, 6410, 8624)})
    n_req = sum(1 for _ in open(F.CACHE / 'requests.jsonl', encoding='utf-8'))
    corpus = {
        'country': {
            'code': 'RW', 'name': 'Rwanda', 'slug': 'rwanda', 'lang': 'en', 'tz': 'Africa/Kigali',
            'future_branch': 'future',
            'publisher': {'name': 'Rwanda Law Reform Commission (amategeko.gov.rw)', 'email': 'rlrc@amategeko.invalid'},
            'default_in_force_rule': {
                'text': 'Constitution (2023) Art. 174(1): "Laws cannot enter into force without their prior publication '
                        'in accordance with procedures determined by law." Every text used here states its own '
                        'commencement on publication in the Official Gazette, and that is the date used.',
                'source': src(3939)},
            'licence_note': 'Legislation in force in Rwanda is "property of Rwanda Law Reform Commission (RLRC)" and '
                            'law reports and judgments are "property of the Judiciary" (amategeko.gov.rw). The texts on '
                            'the site "do not modify the authenticity of the texts of laws published in the Official '
                            'Gazette of the Republic of Rwanda". No open licence is stated.'},
        'sources': [
            {'name': 'Official Gazette of the Republic of Rwanda, via the Rwanda Law Reform Commission API '
                     '(amategeko.gov.rw)',
             'url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/', 'retrieved': retrieved[-1],
             'requests': n_req,
             'licence': 'No open licence; RLRC property (legislation), Judiciary property (law reports). Private repo.',
             'notes': 'Trilingual Gazette PDFs (Kinyarwanda, English, French: all three are official; the laws say they '
                      'were adopted in Ikinyarwanda). English column used. Files: '
                      + ', '.join(f'{f} sha256 {meta(f)["pdf_sha256"][:16]}' for f in (5144, 3939, 4119, 4115, 4073,
                                                                                         4116, 6410, 8624))}],
        'laws': dict(sorted(laws.items())),
        'acts': acts,
        'applies': [],
        'decisions': decisions,
        'ai_use': ['Claude Code (Claude Opus 5.5, claude-opus-5-5) wrote fetch.py, extract.py changes and parse.py and '
                   'chose the sources. No model reads or writes legal text: every unit is extracted by code from the '
                   'PDF text layer. 0 model calls at data-build time.'],
    }
    tmp = HERE / 'corpus.json.tmp'
    tmp.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    tmp.replace(HERE / 'corpus.json')
    for a in acts:
        print(a['slug'], len(a['versions']), 'versions;', ' '.join(v['from'] for v in a['versions']))


if __name__ == '__main__':
    main()
