"""The ENGLISH column of a trilingual Official Gazette PDF (Kinyarwanda | English | French), as structure.

No AI, no fuzzy edits, no guessing: every rule below is positional or textual and is declared in REPRODUCE.md.
  - Running heads and page numbers are removed by CONTENT before the columns are split: on every page, a row of words
    (all columns, grouped by top edge within 3pt) whose text is exactly "Official Gazette n° Special of DD/MM/YYYY", or
    a row that is a bare number in the top or bottom 75pt of the page.
  - Columns: the two gutters are the two interior x-ranges that almost no word box covers over the whole document
    (coverage <= 5% of the busiest x); a word belongs to the English column when its centre lies between them.
  - Lines: English-column words of one page grouped by their top edge (within 3pt), sorted left to right, joined by
    one space. Soft hyphens (U+00AD) are removed.
  - Paragraphs, within a page: a new paragraph starts when the vertical step from the previous line exceeds 1.5 times
    the document's usual line pitch (the median step), or when the line starts a list item ("1° ", "a) ").
  - Paragraphs, across a page break (no vertical step to measure), first rule that applies:
      1. the next line starts a unit ("Article N:", "CHAPTER", "Section", "Subsection", "1°", "a)", "(a)", or "(1) "
         followed by a capital letter) -> new paragraph;
      2. the next line starts with a lowercase letter -> same paragraph;
      3. the previous line ends with . ; or : (closing quotes and brackets ignored) -> new paragraph;
      4. the paragraph so far is a heading (Article/CHAPTER/Section/Subsection line) or is in capitals -> new paragraph;
      5. otherwise -> same paragraph (the sentence runs on).
  - Structure: the table of contents ends with its entry for the highest-numbered article; the body is everything
    after that paragraph, up to the signature block ("Kigali, on ..." or "(Sé)"/"(sé)"). "CHAPTER ...:",
    "Section ...:", "Subsection ...:" and "Article ...:" paragraphs open (a CHAPTER/Section paragraph inside an article
    counts only when it has at most 4 lines, or, for CHAPTER, is all in capitals) a chapter, section, subsection and article
    ("Artile" is read as "Article": the 2015 text misprints the heading of Article 11). The paragraphs before the
    first article are the introduction: the enacting formula, then from "PREAMBLE" (if printed) the preamble.
Letter-spaced text (five or more consecutive one-letter words) stops the extraction; neither text used has any.
Needs PyMuPDF (import pymupdf).
"""
import re
import statistics

HEADER = re.compile(r'^Official Gazette (?:n°|no\.) Special of \d\d/\d\d/\d{4}$')
PAGE_NO = re.compile(r'^\d{1,3}$')
ART = re.compile(r'^Arti?c?le (One|one|\d+)\s*:\s*(.*)$', re.S)
ART_LOOSE = re.compile(r'^Arti?le (One|\d+)\s*:')
CHAP = re.compile(r'^CHAPTER (ONE|[IVXL]+)\s*:\s*(.*)$', re.S)
SECT = re.compile(r'^Section (One|\d+)\s*:\s*(.*)$', re.S)
SUBS = re.compile(r'^Sub[- ]?section (One|\d+)\s*:\s*(.*)$', re.S)
SIGN = re.compile(r'^(Kigali, on |\(Sé\)|\(sé\))')
UNIT = re.compile(r'^(Arti?c?le (One|\d+)\s*:|CHAPTER |Section |Sub[- ]?section |\d+°|[a-z]\) |\([a-z]\) |\(\d+\) [A-Z])')
ITEM = re.compile(r'^(\d+°|[a-z]\)) ')
HEADING = re.compile(r'^(Arti?c?le (One|\d+)\s*:|CHAPTER |Section |Sub[- ]?section )')
TERMINAL = re.compile(r'[.;:][”"’)]*$')
LETTERS = re.compile(r'(?:^| )(?:\S ){5,}')
SHY = '­'


class ExtractError(Exception):
    pass


def artnum(s: str) -> int:
    return 1 if s in ('One', 'one') else int(s)


def rows_of(words: list) -> list:
    rows = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        if rows and abs(w[1] - rows[-1][0]) < 3:
            rows[-1][1].append(w)
        else:
            rows.append([w[1], [w]])
    for r in rows:
        r[1].sort(key=lambda w: w[0])
    return rows


def page_words(page) -> list:
    """Words of a page with running heads and page numbers removed (by content)."""
    H = page.rect.height
    keep = []
    for y, ws in rows_of(page.get_text('words')):
        text = ' '.join(w[4] for w in ws)
        if HEADER.match(text):
            continue
        if PAGE_NO.match(text) and (y < 75 or max(w[3] for w in ws) > H - 75):
            continue
        keep += ws
    return keep


def gutters(pages: list, W: int) -> tuple:
    """(left, right): the x-range of the English (middle) column."""
    cov = [0] * (W + 2)
    for words in pages:
        for x0, y0, x1, y1, *_ in words:
            for x in range(max(0, int(x0)), min(W, int(x1)) + 1):
                cov[x] += 1
    low = max(cov) * 0.05
    runs, start = [], None
    for x in range(W + 2):
        if cov[x] <= low:
            if start is None:
                start = x
        elif start is not None:
            if x - start >= 4 and start > 20 and x < W - 20:
                runs.append((start, x - 1))
            start = None
    merged = []
    for r in runs:  # a gutter interrupted by a few indented list numbers ("1°") is still one gutter
        if merged and r[0] - merged[-1][1] <= 12:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    if len(merged) != 2:
        raise ExtractError(f'expected two interior gutters, found {runs}')
    # The English column is everything between the outer edges of the two gutters: a word whose centre lies inside a
    # gutter (an indented item number) belongs to the middle column, whose neighbours end before the gutter starts.
    return merged[0][0], merged[1][1]


def lines(doc) -> list:
    """[(page, y0, y1, x0, x1, text)] of the English column."""
    pages = [page_words(p) for p in doc]
    left, right = gutters(pages, int(doc[0].rect.width))
    out = []
    for pn, words in enumerate(pages):
        words = [w for w in words if left < (w[0] + w[2]) / 2 < right]
        for y, ws in rows_of(words):
            text = ' '.join(w[4] for w in ws).replace(SHY, '')
            if text.strip():
                out.append((pn + 1, y, max(w[3] for w in ws), ws[0][0], max(w[2] for w in ws), ' '.join(text.split())))
    return out


def paragraphs(ls: list) -> list:
    """[[line, line, ...]] grouped by the declared rules."""
    steps = [b[1] - a[1] for a, b in zip(ls, ls[1:]) if a[0] == b[0] and 0 < b[1] - a[1] < 40]
    pitch = statistics.median(steps)
    paras, cur = [], []
    for line in ls:
        if not cur:
            cur = [line]
            continue
        prev = cur[-1]
        if prev[0] == line[0]:
            cont = (line[1] - prev[1]) <= 1.5 * pitch and not ITEM.match(line[5])
        else:
            t, so_far = line[5], ' '.join(l[5] for l in cur)
            if UNIT.match(t):
                cont = False
            elif t[:1].islower():
                cont = True
            elif TERMINAL.search(prev[5]):
                cont = False
            elif HEADING.match(so_far) or so_far == so_far.upper():
                cont = False
            else:
                cont = True
        if cont:
            cur.append(line)
        else:
            paras.append(cur)
            cur = [line]
    paras.append(cur)
    return paras


def ptext(p: list) -> str:
    return ' '.join(l[5] for l in p)


def structure(doc) -> dict:
    """{'enacting': [str], 'preamble': [str], 'items': [('chapter'|'section'|'subsection', str) |
    ('article', {num, key, heading, chapter, section, subsection, paras})], 'top', 'lines', 'body_words', 'signature'}"""
    ls = lines(doc)
    paras = paragraphs(ls)
    texts = [ptext(p) for p in paras]
    for t in texts:
        if LETTERS.search(t):
            raise ExtractError('letter-spaced text: ' + t[:80])
    nums = [artnum(m.group(1)) for t in texts for m in [ART.match(t)] if m]
    top = max(nums)
    toc_end = next(i for i, t in enumerate(texts) if ART.match(t) and artnum(ART.match(t).group(1)) == top)
    body = paras[toc_end + 1:]
    end = next((i for i, p in enumerate(body) if SIGN.match(ptext(p))), len(body))
    signature = [ptext(p) for p in body[end:]]
    body = body[:end]
    intro, items = [], []
    chapter = section = subsection = ''
    art = None
    for p in body:
        t = ptext(p)
        m = ART.match(t)
        if m:
            art = {'num': m.group(1), 'key': artnum(m.group(1)), 'heading': ' '.join(m.group(2).split()),
                   'printed': t, 'chapter': chapter, 'section': section, 'subsection': subsection, 'paras': []}
            items.append(('article', art))
            continue
        if CHAP.match(t) and (art is None or len(p) <= 4 or t == t.upper()):
            chapter, section, subsection = t, '', ''
            items.append(('chapter', t))
            art = None
            continue
        if SECT.match(t) and (art is None or len(p) <= 4):
            section, subsection = t, ''
            items.append(('section', t))
            art = None
            continue
        if SUBS.match(t) and (art is None or len(p) <= 4):
            subsection = t
            items.append(('subsection', t))
            art = None
            continue
        if art is None:
            if items:
                raise ExtractError('text between a heading and the next article: ' + t[:80])
            intro.append(t)
        else:
            art['paras'].append(t)
    arts = [a for k, a in items if k == 'article']
    keys = [a['key'] for a in arts]
    if keys != list(range(1, top + 1)):
        bad = next(((i, k) for i, k in enumerate(keys, 1) if i != k), None)
        raise ExtractError(f'article sequence broken at {bad} ({len(keys)} articles, highest {top})')
    empty = [a['key'] for a in arts if not a['paras']]
    if empty:
        raise ExtractError(f'articles without text: {empty}')
    k = intro.index('PREAMBLE') if 'PREAMBLE' in intro else len(intro)
    body_lines = [l for p in body for l in p]
    return {'enacting': intro[:k], 'preamble': intro[k:], 'items': items, 'top': top, 'lines': ls,
            'signature': signature, 'body_words': [w for l in body_lines for w in l[5].split()]}


def flatten(st: dict) -> list:
    """The body's paragraphs in document order (for the word check)."""
    out = st['enacting'] + st['preamble']
    for kind, it in st['items']:
        out += [it['printed']] + it['paras'] if kind == 'article' else [it]
    return out
