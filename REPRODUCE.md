# Reproducing this repository

Built by `tools/build.py` from the Rwanda Law Reform Commission's open API on amategeko.gov.rw. Data retrieved
2026-10-28. robots.txt allows all agents (`User-agent: *`, empty `Disallow:`).

## Sources

`https://apis.amategeko.gov.rw/v1/site/documents-files/<file id>` returns JSON. Its `file_url` is a signed link
(valid one hour) to the Gazette PDF. `tools/source.py` caches the PDF under its file id and the JSON without the
signed link, so `--offline` rebuilds are byte-identical.

| Tag | Source | PDF SHA-256 |
|---|---|---|
| constitution/2015 | https://apis.amategeko.gov.rw/v1/site/documents-files/5144 | `1a4a2fb4c74cfc3db29e419a0dfb66c0f68822574b2f41d6e0f66b580d8b202b` |
| law-2020-017/2020-017 | https://apis.amategeko.gov.rw/v1/site/documents-files/4423 | `241f0fe51edc0d93226188fa38d0252fba33797c4e4995b81594913272f40c7d` |
| law-2020-017/2020-019 | https://apis.amategeko.gov.rw/v1/site/documents-files/4193 | `3c38f4f2c6b01f6e43b84983b1887c002f4d6bb2c1924b5f901b8417eb8d5594` |
| constitution/2023 | https://apis.amategeko.gov.rw/v1/site/documents-files/3939 | `1da4499ef20fa31f634abbdc08e09117fbf67190ac91450e95972265d13cbbc8` |
| law-2020-017/2024-052 | https://apis.amategeko.gov.rw/v1/site/documents-files/6109 | `0bc5ffcc9288a6c565275675c80f99162101643516949c5adc800f68817fc148` |
| law-2020-017/2026-017 | https://apis.amategeko.gov.rw/v1/site/documents-files/11115 | `f22acdea32cba0d406a2e6e50feec3567d455c5d234bd72f222fde0796fae5db` |

Not used: the 2003 original (file 10837) is an image-only scan (170 pages, no text). Amendment no. 1 of 2003 (5149) is
an OCR layer with visible errors. The amendments of 2005 (5131), 2008 (5132) and 2010 (11489) cannot be replayed
without the 2003 base.

## Steps

```
pip install pymupdf==2.0   # as used for this build; Python 3.12.10
python -X utf8 tools/build.py --repo <dir> [--offline] --today 2026-10-28
python -X utf8 tools/check_repo.py --repo <dir>
python -X utf8 tools/test_repo.py --repo <dir>
python -X utf8 tools/build.py --repo <dir> --verify-rebuild --today 2026-10-28
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

- check_repo: 6 law commits; 728 file comparisons against the official texts; word checks 5144:equal, 3939:equal, 4423:equal, 4193:equal, 6109:equal, 11115:equal, constitution/2015 files:equal, law-2020-017/2020-017 files:equal, constitution/2023 files:equal; 0 problems
- test_repo: 6/6 passed
- determinism: `--verify-rebuild` gives the same `main` hash
