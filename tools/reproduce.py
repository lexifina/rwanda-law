"""Writes README.md, LICENSE, REPRODUCE.md, corpus.json and tools/ into the built repository (called by build.py)."""
import json
import shutil
from pathlib import Path

TERMS = ('All the content of this website is divided into two categories: legislation in force in Rwanda including '
         'international treaties and agreements ratified or acceded to by Rwanda and abrogated laws are property of '
         'Rwanda Law Reform Commission (RLRC) while Law reports and judgments are property of the Judiciary. These two '
         'are the only institutions allowed to make changes and updates on different features of this website.')
TERMS2 = ('The laws contained in this website, in any way, do not modify the authenticity of the texts of laws '
          'published in the Official Gazette of the Republic of Rwanda and therefore cannot replace them.')
TOOLS = ['on_date.py', 'build.py', 'extract.py', 'source.py', 'reproduce.py', 'check_repo.py', 'test_repo.py']


def write_docs(repo: Path, evs: list, today: str, here: Path):
    law_days = [e[0] for e in evs]
    record_to = max(d for d in law_days if d <= today)
    (repo / 'tools').mkdir(exist_ok=True)
    for t in TOOLS:
        src = here / t
        (repo / 'tools' / t).write_text(src.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    rows = '\n'.join(f'| {e[0]} | `{e[7]}` | {e[4]} | {e[2]} |' for e in evs)
    readme = f"""# Rwandan law as git history (private)

Two Rwandan texts, in English, as a git history: each commit is a law taking effect.

- `constitution/` holds the Constitution of the Republic of Rwanda. **The record starts with the 2015 revision.** The
  2003 original and its 2003, 2005, 2008 and 2010 amendments are on amategeko.gov.rw only as scans: the 2003 original
  has no text layer, and amendment no. 1 has only a machine-read OCR layer. So no checkable text exists for them. The
  2023 revising act restates the whole Constitution, so that commit is a labelled whole-text replacement.
- `law-2020-017/` holds Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants, with
  its three amending laws (019/2020, 052/2024, 017/2026) replayed article by article.

One file per article (`art-021-bis.md` is Article 21 bis), one paragraph per line. The first line is the article
heading as printed; then `Chapter:`, `Section:` and `Subsection:` lines give its place.

## The questions, as git commands

| Question | Command |
|---|---|
| What did Article 21 bis of the public servants statute say on 1 January 2024? | `python tools/on_date.py 2024-01-01 law-2020-017 21bis` |
| What did Article 9 say on 1 January 2024? | `python tools/on_date.py 2024-01-01 law-2020-017 9` |
| What did Article 3 of the Constitution say on 1 January 2020? | `python tools/on_date.py 2020-01-01 constitution 3` |
| Which law wrote each line of Article 21 bis? | `git blame main -- law-2020-017/art-021-bis.md` |
| Which laws changed Article 21 bis, newest first? | `git log --follow --format="%ad %an" --date=short main -- law-2020-017/art-021-bis.md` |
| What did Law n° 052/2024 change? | `git show --stat law-2020-017/2024-052` |
| Word by word, what did it change? | `git show --word-diff law-2020-017/2024-052 -- law-2020-017/art-009.md` |
| Which commits are in the record, with their in-force days? | `git log --format="%(trailers:key=In-force,valueonly,separator=) %an" main` |
| The newest commit in force by the end of 2023 (UTC)? | `git rev-list -n 1 --before="2023-12-31T23:59:59Z" main` |
| Every tag (one per law)? | `git tag` |

## The dates

| In force | Tag | Author (the law) | Folder |
|---|---|---|---|
{rows}

- **The commit date is the in-force day**, at 12:00 in Kigali (CAT, UTC+2; Rwanda has no summer time). Each in-force
  day comes from the text's own final article (for example "This Law comes into force on the date of its publication
  in the Official Gazette of the Republic of Rwanda") together with the Gazette's running head ("Official Gazette n°
  Special of DD/MM/YYYY"). Both are quoted in each commit's `Evidence:` trailer.
- Other dates go in trailers: `Published:` and, where printed in English, `Promulgated:`. Law n° 019/2020 also says it
  "takes effects as of 8 October 2020", before it was published. The commit keeps its in-force day (20 November 2020)
  and records the earlier day in `Takes-effect:`.
- Use `--before="YYYY-MM-DDT23:59:59Z"`. A bare date takes the current time of day, so the answer for a noon commit
  flips at noon.
- In PowerShell, quote the whole revision:path argument, for example
  `$r = git rev-list -n 1 --before="2023-12-31T23:59:59Z" main; git show "$($r):law-2020-017/art-009.md"`, or
  PowerShell splits it in two.

## How it is checked

`tools/check_repo.py` rebuilds every version from the cached Gazette PDFs and compares it with the repository.
- Each file is checked byte for byte against the extraction of its official text.
- A word check joins the paragraphs with spaces and compares the result with the column's own words.
- Each amending law's restated text must appear, line by line, in its commit. Articles the law does not name must stay
  byte-identical.

The build is deterministic: rebuilding from the cache gives the same commit hashes (`build.py --verify-rebuild`).
`tools/test_repo.py` runs every command in the table above.

## What "author" means

The author of a commit is the law that made the change, with an address that cannot exist (`…@amategeko.invalid`).
So `git blame` names, for every line, the law that last wrote it. Blame credits whole lines (whole paragraphs here):
a paragraph rewritten by a later law is credited entirely to that law. Use `--word-diff` for the detail. The committer
is always Lexifina.

## What it does not show

- **The Constitution before the 2015 revision**, which exists only as scans. Its 2023 replacement is credited as a
  whole: the 2023 act renumbers the Constitution, so `art-NNN.md` can hold a different provision after 2023.
- **Official consolidations of Law n° 017/2020.** None is published, so the versions after 2020 are replayed from the
  amending laws and are not checked against one. Where an amending law restates only the body of an article
  (Articles 9, 21, 3 and 4), the heading stays as enacted.
- **Kinyarwanda and French.** Kinyarwanda is the language the laws were drafted, considered and adopted in. This record
  is the English column only.
- **Instruments made under these laws** (Presidential, Prime Minister's and Ministerial Orders).

## How it is built

See REPRODUCE.md. In short: `python -X utf8 tools/build.py --offline --repo .` from a checkout that holds the cache.

## Licence and terms

There is no licence. amategeko.gov.rw says:

> {TERMS}
>
> {TERMS2}

This repository is private. **Ask the Rwanda Law Reform Commission (RLRC) before publishing it.** The Official Gazette
is the authentic text.
"""
    (repo / 'README.md').write_text(readme, encoding='utf-8', newline='\n')
    (repo / 'LICENSE').write_text(
        'No licence is granted.\n\nThe texts are from amategeko.gov.rw, whose terms of use say:\n\n'
        f'"{TERMS}"\n\n"{TERMS2}"\n\nThe reuse terms are unclear. This repository is private; ask the Rwanda Law Reform '
        'Commission (RLRC) before publishing it.\n\nThe tools in tools/ are by Lexifina.\n', encoding='utf-8', newline='\n')
    corpus = {
        'corpus': 'rw/national/acts',
        'name': 'Rwandan law: the Constitution (from its 2015 revision) and the general statute governing public servants',
        'label': 'Rwanda',
        'language': 'en',
        'acts': ['constitution', 'law-2020-017'],
        'history_from': min(law_days),
        'record_to': record_to,
        'record_note': ('Constitution from the 2015 revision (2003-2010 texts are scans without a text layer), replaced '
                        'as a whole by the 2023 revising act; Law n° 017/2020 with three amending laws replayed. English '
                        'column of the trilingual Official Gazette; data retrieved ' + today + '.'),
        'in_force_trailer': 'In-force',
        'built': today,
        'dates': {'commit': 'in-force', 'other_trailers': ['Published', 'Promulgated', 'Takes-effect'],
                  'time': '12:00 Africa/Kigali (UTC+2, no summer time)'},
        'scope': {'trailer': None,
                  'when_absent': ('no scope note is recorded in this history; not a statement that a change reaches '
                                  'every case'),
                  'default_reach': {
                      'rule': 'laws apply from publication; criminal law is not retroactive',
                      'meaning': ('a law cannot enter into force before it is published; no one may be punished for an '
                                  'act that was not an offence when committed. A law may still state an earlier effect '
                                  '(Law n° 019/2020: "takes effects as of 8 October 2020")'),
                      'authority': ('Constitution of the Republic of Rwanda (2023), Article 174(1) and Article 29(1)(d); '
                                    'Article 138(1) ("the principle of non- retroactivity of criminal law")'),
                      'decided_here': False}},
        'replayed': True,
        'tool': 'tools/on_date.py',
        'citation': {'file': '([a-z0-9-]+)/art-0*([0-9]+)(?:-bis|-ter|-quater)?\\.md',
                     'cites': '[Aa]rticle {n}([^0-9]|$)'},
    }
    (repo / 'corpus.json').write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + '\n', encoding='utf-8',
                                      newline='\n')
    ver = here / 'verification.json'
    vtxt = json.loads(ver.read_text(encoding='utf-8')) if ver.exists() else {}
    files = '\n'.join(f'| {e[7]} | {e[6].split("Source: ")[1].split(chr(10))[0]} | '
                      f'`{e[6].split("Source-sha256: ")[1].split(chr(10))[0]}` |' for e in evs)
    check = vtxt.get('check', {}).get('summary', '(not recorded yet)')
    smoke = vtxt.get('smoke', {})
    smoke_s = f'{smoke.get("passed")}/{smoke.get("total")} passed' if smoke else '(not recorded yet)'
    import platform
    import pymupdf
    pyver = (pymupdf.__version__, platform.python_version())
    rep = f"""# Reproducing this repository

Built by `tools/build.py` from the Rwanda Law Reform Commission's open API on amategeko.gov.rw. Data retrieved
{today}. robots.txt allows all agents (`User-agent: *`, empty `Disallow:`).

## Sources

`https://apis.amategeko.gov.rw/v1/site/documents-files/<file id>` returns JSON. Its `file_url` is a signed link
(valid one hour) to the Gazette PDF. `tools/source.py` caches the PDF under its file id and the JSON without the
signed link, so `--offline` rebuilds are byte-identical.

| Tag | Source | PDF SHA-256 |
|---|---|---|
{files}

Not used: the 2003 original (file 10837) is an image-only scan (170 pages, no text). Amendment no. 1 of 2003 (5149) is
an OCR layer with visible errors. The amendments of 2005 (5131), 2008 (5132) and 2010 (11489) cannot be replayed
without the 2003 base.

## Steps

```
pip install pymupdf=={pyver[0]}   # as used for this build; Python {pyver[1]}
python -X utf8 tools/build.py --repo <dir> [--offline] --today {today}
python -X utf8 tools/check_repo.py --repo <dir>
python -X utf8 tools/test_repo.py --repo <dir>
python -X utf8 tools/build.py --repo <dir> --verify-rebuild --today {today}
```

## Extraction (tools/extract.py)

The English column of each trilingual PDF is read from PyMuPDF word positions. Every rule is positional or textual
and is listed in extract.py's docstring:
- headers removed by content
- gutters found by word coverage
- paragraph breaks by line pitch, with a declared rule at page breaks
- structure from "CHAPTER", "Section", "Subsection" and "Article" paragraphs

No AI writes or edits any text, and no model runs at build time. The builder was written with an AI coding agent
(Claude, Anthropic; model Opus 5.5, via Claude Code).

## Replay (tools/build.py)

An amending law's article is applied only when its first paragraph matches one of three forms, and is otherwise a
build error:
- "Article N of Law n° 017/2020 ... is amended/modified as follows:", followed by the quoted restated text
- "In Law n° 017/2020 ..., Article N bis is inserted to read as follows:"
- "Article N of Law n° 017/2020 ... is repealed."

Its own language and commencement articles are recognised and skipped. The quotation marks around a restated text
are removed: the opening mark of the first paragraph, and the closing mark of the last, before or after its full stop.

## Results at build time

- check_repo: {check}
- test_repo: {smoke_s}
- determinism: `--verify-rebuild` gives the same `main` hash
"""
    (repo / 'REPRODUCE.md').write_text(rep, encoding='utf-8', newline='\n')
