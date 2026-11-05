"""Source-backed dated history for evidence, contracts, criminal procedure and companies.

Every version is reconstructed from its official PDF text layer. Missing inputs,
unknown replay grammar, source digest changes and incomplete restatements fail.
No OCR or model-written legal text is used.
"""
import collections
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('_rwanda_depth_extract', HERE / 'extract.py')
X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(X)
_source_dir = None
_docs = {}
UNCLOSED = []
CLOSED_BEFORE_STOP = []
BODY_ONLY = []
RESTATED_HEAD = re.compile(r'^Article (\d+)(?: (bis|ter))?\s*:\s*(.+)$')
SKIP = re.compile(r'^(This Law was drafted(?: in English)?, considered and adopted in Ikinyarwanda\.|All prior legal provisions contrary to this Law are repealed\.|This Law comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda\.(?: It takes effects? as of \d{1,2} [A-Z][a-z]+ \d{4}\.)?)$')
COMMENCE = re.compile(r'(?:comes|shall come) into force (?:on the date of its publication|upon promulgation by the President of the Republic and its publication) in the Official Gazette of the Republic of Rwanda')

def grammar(ref):
    return (re.compile(rf'^Article (\d+)(?: (bis|ter))? of {ref} is (?:amended|modified) as follows:$'),
            re.compile(rf'^Article (\d+)(?: (bis|ter))? of {ref} is repealed\.$'),
            re.compile(rf'^In (?:the )?{ref},? (?:there is inserted (?:an )?|(?:an )?)Article (\d+) (bis|ter) (?:is inserted )?(?:which is worded|to read|worded) as follows:$'))

def pdf(fid):
    import pymupdf
    record = next(record for record in VERSIONS if record['file'] == fid)
    path = _source_dir / f'file-{fid}.pdf'
    body = path.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    if digest != record['source_sha256']:
        raise ValueError(f'Official source digest mismatch for {fid}')
    return pymupdf.open(stream=body, filetype='pdf'), digest

def source(fid):
    if fid not in _docs:
        doc, digest = pdf(fid)
        structure = X.structure(doc)
        days = {f'{year}-{month}-{day}' for page in doc for day, month, year in
                re.findall(r'Official Gazette n(?:°|º|o\.) ?(?:Special(?: [Bb]is| [Tt]er)?|\d+ ?(?:[Bb]is|[Tt]er)?) +of (\d\d)/(\d\d)/(\d{4})', page.get_text())}
        record = next(record for record in VERSIONS if record['file'] == fid)
        if days != {record['from']}:
            raise ValueError(f'Gazette date mismatch for {fid}: {days}')
        last = next(item for kind, item in reversed(structure['items']) if kind == 'article')
        if not COMMENCE.search(norm(' '.join(last['paras']))):
            raise ValueError(f'No publication commencement clause for {fid}')
        _docs[fid] = (structure, digest)
    return _docs[fid]

def contexts(text):
    return [line for line in text.splitlines() if line.startswith(('Chapter: ', 'Section: ', 'Subsection: '))]

def snapshots(directory):
    global _source_dir
    _source_dir = Path(directory)
    _docs.clear()
    states = {}
    output = []
    for record in VERSIONS:
        structure, digest = source(record['file'])
        act = record['act']
        if record['history'] == 'as enacted':
            units = {'enacting-formula': {'text': text_of(structure['enacting'])}}
            for kind, article in structure['items']:
                if kind != 'article':
                    continue
                key = art_key(str(article['key']))
                text = text_of([article['printed']] + article['paras'])
                text += ''.join(field.capitalize() + ': ' + norm(article[field]) + '\n'
                                for field in ['chapter', 'section', 'subsection'] if article[field])
                units[key] = {'text': text}
            changes = dict(units)
            states[act] = units
        else:
            BODY_ONLY.clear()
            changes, operations, digest = replay(record['file'], states[act], REFS[act])
            if any(operation == 'repealed-already-absent' for operation, _, _ in operations):
                raise ValueError('An amendment repeals an absent article')
            if len(changes) != {'criminal-procedure': 18, 'companies': 22}[act]:
                raise ValueError(f'Unexpected amended article count for {act}')
            for key, unit in changes.items():
                if unit is None:
                    states[act].pop(key)
                    continue
                context_key = key if key in states[act] else next((old for old in sorted(states[act], reverse=True)
                              if old < key and old.startswith('art-')), None)
                if context_key:
                    unit['text'] += ''.join(line + '\n' for line in contexts(states[act][context_key]['text']))
                states[act][key] = unit
        files = {key + '.md': unit['text'] for key, unit in states[act].items()}
        output.append((record, files, changes))
    return output

def events(directory):
    return [(record['from'], 2, record['act'], files, record['law'],
             f"law-{record['tag'].split('/')[-1]}@amategeko.invalid", '', record['tag'])
            for record, files, changes in snapshots(directory)]

def raw_strings(doc):
    counts = collections.Counter(round(word[0]) for page in doc for word in page.get_text('words'))
    width = collections.Counter(round(page.rect.width) for page in doc).most_common(1)[0][0]
    margins = []
    for lower, upper in [(0.05, 0.16), (0.34, 0.42), (0.60, 0.69)]:
        band = {x: count for x, count in counts.items() if lower * width <= x <= upper * width}
        peak = max(band.values())
        margins.append(min(x for x, count in band.items() if count >= peak * 0.2))
    low, high = margins[1] - 10, margins[2] - 10
    output = []
    for page in doc:
        selected = []
        rows = []
        for word in sorted(page.get_text('words'), key=lambda word: (word[1], word[0])):
            if rows and abs(word[1] - rows[-1][0]) < 3:
                rows[-1][1].append(word)
            else:
                rows.append([word[1], [word]])
        for y, words in rows:
            words.sort(key=lambda word: word[0])
            text = ' '.join(word[4] for word in words)
            if X.HEADER.match(text) or (re.fullmatch(r'\d{1,3}', text) and (y < 75 or max(word[3] for word in words) > page.rect.height - 75)):
                continue
            selected.extend(word for word in words if low <= (word[0] + word[2]) / 2 < high)
        english_rows = []
        for word in sorted(selected, key=lambda word: (word[1], word[0])):
            if english_rows and abs(word[1] - english_rows[-1][0]) < 3:
                english_rows[-1][1].append(word)
            else:
                english_rows.append([word[1], [word]])
        for y, words in english_rows:
            output.extend(word[4] for word in sorted(words, key=lambda word: word[0]))
    return norm(' '.join(output))

def body_text(files):
    output = [files.get('enacting-formula.md', ''), files.get('preamble.md', '')]
    previous = {}
    for name in sorted(name for name in files if name.startswith('art-')):
        current, body = {}, []
        for line in files[name].splitlines():
            if line.startswith(('Chapter: ', 'Section: ', 'Subsection: ')):
                kind, value = line.split(': ', 1)
                current[kind] = value
            else:
                body.append(line.removeprefix('# '))
        for kind in ['Chapter', 'Section', 'Subsection']:
            if current.get(kind) and current.get(kind) != previous.get(kind):
                output.append(current[kind])
        previous = current
        output.extend(body)
    return norm(' '.join(output))

def restatement_matches(body, official):
    """Compare every restatement character, accounting only for its outer quotes.

    The Gazette can put the opening delimiter after an initial '(1) ' and
    the closing delimiter immediately before the final full stop. Those are
    exactly the two boundary forms unquote() removes; internal quotes remain.
    """
    candidates = {body}
    prefix = re.match(r'^(\(\d+\) )', body)
    if prefix:
        candidates.add(body[:prefix.end()] + '"' + body[prefix.end():])
        candidates.add(body[:prefix.end()] + '" ' + body[prefix.end():])
    if body.endswith('.'):
        boundary_forms = list(candidates)
        candidates.update(candidate[:-1] + '".' for candidate in boundary_forms)
        candidates.update(candidate[:-1] + ' ".' for candidate in boundary_forms)
    return any(candidate in official for candidate in candidates)

def check_sources(directory):
    problems, checks = [], []
    for record, files, changes in snapshots(directory):
        doc, digest = pdf(record['file'])
        official = raw_strings(doc)
        if record['history'] == 'as enacted':
            body = body_text(files)
            if body not in official:
                problems.append(f"{record['tag']}: complete enacted body differs from the official column")
            checks.append(f"{record['tag']}: {len(body)} source characters; complete body equal={body in official}")
        else:
            matched = 0
            for key, unit in changes.items():
                if unit is None:
                    continue
                body = norm(' '.join(line for line in unit['text'].splitlines()[1:]
                            if not line.startswith(('Chapter: ', 'Section: ', 'Subsection: '))))
                if not restatement_matches(body, official):
                    problems.append(f"{record['tag']}: restated body of {key} differs from official column")
                else:
                    matched += 1
            checks.append(f"{record['tag']}: {matched}/{len(changes)} restated bodies equal")
        images = [(index + 1, image[0]) for index, page in enumerate(doc) for image in page.get_images()]
        if any(page != 1 for page, xref in images):
            problems.append(f"{record['tag']}: normative image review required: {images}")
    return problems, checks

VERSIONS = [{'act': 'evidence', 'from': '2024-06-27', 'history': 'as enacted', 'law': 'Law n° 062/2024', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/6138', 'source_sha256': '5bf080d2e5bceab25859d73450b9689e1bab3ea7d6a702401bd993abfe5cf04d', 'in_force_basis': 'Evidence Law: Law n° 062/2024 in force 2024-06-27 (Article 96: Entry into force comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). 97 units as enacted.', 'file': 6138, 'tag': 'evidence/2024-062'}, {'act': 'contracts', 'from': '2012-01-23', 'history': 'as enacted', 'law': 'Law n° 45/2011', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/4724', 'source_sha256': '31f62ae22d11e6a6b5ed9f2f47e159d13bef73bb10d1a2db28036600aac99f30', 'in_force_basis': 'Contracts Law: Law n° 45/2011 in force 2012-01-23 (Article 165: Commencement shall come into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). 166 units as enacted.', 'file': 4724, 'tag': 'contracts/2011-045'}, {'act': 'criminal-procedure', 'from': '2019-11-08', 'history': 'as enacted', 'law': 'Law n° 027/2019', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/4176', 'source_sha256': 'ce1f3b1fd50bb472ecf76d58f9e8d24ec2e964aef14970c48fe0c61b1f51bb52', 'in_force_basis': 'Criminal Procedure Law: Law n° 027/2019 in force 2019-11-08 (Article 267: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). 268 units as enacted.', 'file': 4176, 'tag': 'criminal-procedure/2019-027'}, {'act': 'criminal-procedure', 'from': '2023-12-05', 'history': 'replayed', 'law': 'Law n° 058/2023', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/4154', 'source_sha256': '83782551a1770c51d5a8d256c409271a0f3e03a6f6e513dcfdd416106eeb9715', 'in_force_basis': 'Criminal Procedure Law: Law n° 058/2023 in force 2023-12-05 (Article 20: Entry into force comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 15; Art. 2 amended Article 16; Art. 3 inserted Article 16 bis; Art. 4 amended Article 17; Art. 5 amended Article 24; Art. 6 amended Article 49; Art. 7 amended Article 58; Art. 8 amended Article 70; Art. 9 amended Article 72; Art. 10 amended Article 76; Art. 11 inserted Article 169 bis; Art. 12 amended Article 173; Art. 13 amended Article 174; Art. 14 amended Article 199; Art. 15 amended Article 216; Art. 16 amended Article 233; Art. 17 amended Article 234; Art. 18 inserted Article 264 bis.', 'file': 4154, 'tag': 'criminal-procedure/2023-058'}, {'act': 'companies', 'from': '2021-02-08', 'history': 'as enacted', 'law': 'Law n° 007/2021', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/5095', 'source_sha256': 'ac85f49abff32c6907dbcd7aa95fd858ad366619f31d9850cbc8163f6fee4e68', 'in_force_basis': 'Companies Law: Law n° 007/2021 in force 2021-02-08 (Article 362: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). 363 units as enacted.', 'file': 5095, 'tag': 'companies/2021-007'}, {'act': 'companies', 'from': '2023-03-30', 'history': 'replayed', 'law': 'Law n° 019/2023', 'source_url': 'https://apis.amategeko.gov.rw/v1/site/documents-files/5053', 'source_sha256': 'a69c57cc013db304ff7106cbc61d632e8e7b7659eafba077047a70f49d45955c', 'in_force_basis': 'Companies Law: Law n° 019/2023 in force 2023-03-30 (Article 24: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 2; Art. 2 amended Article 19; Art. 3 amended Article 57; Art. 4 amended Article 111; Art. 5 amended Article 114; Art. 6 amended Article 115; Art. 7 amended Article 116; Art. 8 inserted Article 116 bis; Art. 9 inserted Article 116 ter; Art. 10 amended Article 120; Art. 11 amended Article 143; Art. 12 amended Article 172; Art. 13 amended Article 247; Art. 14 amended Article 252; Art. 15 amended Article 257; Art. 16 amended Article 269; Art. 17 amended Article 287; Art. 18 amended Article 288; Art. 19 amended Article 326; Art. 20 amended Article 327; Art. 21 amended Article 352; Art. 22 inserted Article 354 bis.', 'file': 5053, 'tag': 'companies/2023-019'}]
REFS = {'criminal-procedure': '(?:the )?Law n° ?027/2019 of 19/09/2019 relating to the criminal procedure', 'companies': '(?:the )?Law n° ?007/2021 of 05/02/2021 governing companies'}

X.HEADER = re.compile(r'^Official Gazette n(?:°|º|o\.) ?(?:Special(?: [Bb]is| [Tt]er)?|\d+ ?(?:[Bb]is|[Tt]er)?) +of \d\d/\d\d/\d{4}$')
X.SUBS = re.compile(r'^Sub-?[Ss]ection (One|\d+)\s*:\s*(.*)$', re.S)
X.ART = re.compile(r'^Arti?c?les?[ _](One|one|\d+)(?:\s*:\s*|\s+(?=[A-Z]))(.*)$', re.S)
X.HEADING = re.compile(r'^(Arti?c?les? (One|\d+)\s*:|CHAPTER |Section |Sub-?[Ss]ection )')
X.UNIT = re.compile(r'^(Arti?c?les? (One|\d+)\s*:|CHAPTER |Section |Sub-?[Ss]ection |\d+°|[a-z]\) |\([a-z]\) |\(\d+\) [A-Z])')

_paragraphs = X.paragraphs
DANGLING = {'the', 'of', 'and', 'to', 'for', 'in', 'on', 'by', 'a', 'an', 'with', 'or'}


def _paragraphs_split_articles(ls: list) -> list:
    """extract.paragraphs, plus one rule: an "Article N:" line that follows a line ending a sentence starts a new
    paragraph even when the line gap is small (these texts print some article headings close under the text above)."""
    out = []
    for para in _paragraphs(ls):
        cur = [para[0]]
        for prev, line in zip(para, para[1:]):
            if X.ART.match(line[5]) and X.TERMINAL.search(prev[5]):
                out.append(cur)
                cur = [line]
            else:
                cur.append(line)
        out.append(cur)
    # A CHAPTER/Section heading carried over a page break: its upper-case continuation is part of the heading.
    merged = []
    for para in out:
        t = ' '.join(l[5] for l in para)
        if merged and t.isupper() and not X.UNIT.match(t) and len(t) < 160:
            pt = ' '.join(l[5] for l in merged[-1])
            if (X.CHAP.match(pt) or X.SECT.match(pt) or X.SUBS.match(pt)) and pt == pt.upper():
                merged[-1] = merged[-1] + para
                continue
        # a mixed-case Section heading cut after a dangling word ("... delivered to the" | "Registrar General")
        if merged and not X.UNIT.match(t) and len(t) < 80:
            pt = ' '.join(l[5] for l in merged[-1])
            if (X.SECT.match(pt) or X.SUBS.match(pt)) and pt.split()[-1] in DANGLING:
                merged[-1] = merged[-1] + para
                continue
        merged.append(para)
    return merged


X.paragraphs = _paragraphs_split_articles



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

def unquote(paras: list) -> list:
    ps = list(paras)
    m = re.match(r'^(\(\d+\) )?"\s*', ps[0])
    if not m:
        raise SystemExit('restated text without an opening quote: ' + ps[0][:80])
    ps[0] = (m.group(1) or '') + ps[0][m.end():]
    if ps[-1].endswith('".'):          # the closing mark printed before the amending sentence's full stop
        CLOSED_BEFORE_STOP.append(ps[0][:60])
        ps[-1] = ps[-1][:-2].rstrip() + '.'
        return ps
    if not ps[-1].endswith('"'):
        raise ValueError('Restated text has no closing quotation mark')
    ps[-1] = ps[-1][:-1].rstrip()
    return ps

def replay(fid: int, prev: dict, ref: str) -> tuple[dict, list, str]:
    """(changes, ops, sha256): the changes an amending law makes to prev's units."""
    AMEND, REPEAL, INSERT = grammar(ref)
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
            k = art_key(m_r.group(1), m_r.group(2) or '')
            if k in prev:
                changes[k] = None
                ops.append(('repealed', k, it['key']))
            else:
                ops.append(('repealed-already-absent', k, it['key']))
            continue
        if m_a or m_i:
            k = art_key(m_a.group(1), m_a.group(2) or '') if m_a else art_key(m_i.group(1), m_i.group(2))
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
                BODY_ONLY.append((it['key'], k))
            else:
                raise SystemExit(f'file {fid} art {it["key"]}: inserted article without a heading')
            if m_i and k in prev:
                raise SystemExit(f'file {fid}: inserts {k}, which exists')
            changes[k] = {'label': art_label(k), 'kind': 'art', 'text': text_of(lines)}
            ops.append(('inserted' if m_i else 'amended', k, it['key']))
            continue
        raise SystemExit(f'file {fid} art {it["key"]}: not in the replay grammar: {first[:120]}')
    return changes, ops, sha
