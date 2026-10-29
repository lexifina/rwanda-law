# How this repository was made (Rwanda)

This file is written by the build on 2026-10-29, the day the source data was retrieved. Everything below is enough to rebuild this repository hash for hash.

## Sources

| Source | Address | Retrieved | Requests | Licence |
| --- | --- | --- | ---: | --- |
| Official Gazette of the Republic of Rwanda, via the Rwanda Law Reform Commission API (amategeko.gov.rw) | <https://apis.amategeko.gov.rw/v1/site/documents-files/> | 2026-10-29 | 44 | No open licence; RLRC property (legislation), Judiciary property (law reports). Private repo. |

Every response is cached by the sha256 of its URL, and the table above lists every source with its retrieval date. Lexifina keeps its fetch scripts privately; `tools/parse.py` reads only the cache and writes `corpus.json`, so the same cache always gives the same corpus.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `constitution` | The Constitution of the Republic of Rwanda | 2 | 2015-12-24 to 2023-08-04 |
| `penal-code` | Law n° 68/2018 of 30/08/2018 determining offences and penalties in general | 5 | 2018-09-27 to 2023-12-05 |
| `data-protection` | Law n° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy | 1 | 2021-10-15 to 2021-10-15 |
| `public-servants` | Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants | 4 | 2020-10-08 to 2026-04-24 |

The build made 12 commits:

| Commits | Kind |
| ---: | --- |
| 4 | first version of an act |
| 8 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `future`: laws not yet in force on 2026-10-29.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 13 laws in the record.
- 24 tags.

## Dates

Each commit is dated at noon (Africa/Kigali) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: Constitution (2023) Art. 174(1): "Laws cannot enter into force without their prior publication in accordance with procedures determined by law." Every text used here states its own commencement on publication in the Official Gazette, and that is the date used. https://apis.amategeko.gov.rw/v1/site/documents-files/3939

## Commands, in order

```sh
# fill the cache from the sources listed above (network; Lexifina's fetch scripts are kept privately)
python -X utf8 tools/parse.py                  # cache -> corpus.json (no network)
python -X utf8 tools/build.py <folder> --repo <empty folder> --docs-date 2026-10-29
python -X utf8 tools/check_repo.py <repo> --corpus <folder>/corpus.json --write
python -X utf8 tools/build.py <folder> --repo <another empty folder> --docs-date 2026-10-29 --compare <repo>
```

In the main Lexifina repository these files live as follows:
- `fetch.py`, `parse.py` and `repo/`: in `scripts/rwanda-law/`.
- `build.py`, `check_repo.py` (`check.py` there) and `on.py`: in `scripts/gitlaw_common/`, with the corpus format in `SCHEMA.md`.

## Exact inputs

- `corpus.json` sha256 `fa3996c27c82b2642868229326ea84ff7deacbc10411eb56316414946755e06e` (640718 bytes)
- Script blob hashes (`git hash-object`):

| Script | Blob |
| --- | --- |
| build.py | `2bfc4ac9df193a7be844556d7f69cdb9d93ec3f2` |
| check.py | `cd346c7ff9996d450240e3bab52bcae03b2bc865` |
| on.py | `644a6c0857fbcc72562032b58d57aa113fee0641` |
| fetch.py | `73d4545a587514d450f3a203153c799b37bf2899` |
| parse.py | `8e2464ab03dc58827ef12eaa11225a4a7fb36aab` |

- Tools:
  - Python 3.14.0
  - git version 2.52.0.windows.1
  - curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP

## Checks

12 versions of 4 acts read back from git on the day each took effect and on the day before: 0 mismatches. Trailers: 0 commits whose trailers git cannot parse. Health: 0 merge commits on main, 0 commit dates that go backwards, 0 commits dated after the build.

A second build from the same corpus into an empty folder gave identical hashes for all 12 history commits and 24 tags (history tip `ce0185cb691e4360a70fd7d0fdab3457e8347c25`).

These results are from the check run on the build before this one, from the same corpus.

## Decisions made by hand

- Constitution: in force 2015-12-24 (Article 177: Commencement of this Constitution comes into force upon promulgation by the President of the Republic and its publication in the Official Gazette of the Republic of Rwanda; promulgated "Kigali, on 24/12/2015"; Gazette running head) and 2023-08-04 (Article 176: Entry into force comes into force upon promulgation by the President of the Republic and its publication in the Official Gazette of the Republic of Rwanda; Gazette running head "Official Gazette n° Special of 04/08/2023").
- Constitution: the 2023 revision is treated as one whole-text replacement credited to it, compared article number by article number with the 2015 text.
- Constitution: the record starts with the 2015 revision. The 2003 Constitution (file 10837) is an image-only scan with no text layer, and amendment no. 1 of 2003 (file 5149) carries only an OCR layer, so neither is used (no OCR). The amendments of 2005 (5131), 2008 (5132) and 2010 (11489) have text layers but cannot be replayed without the 2003 base text.
- Law n° 69/2019: in force 2019-11-29 (Article 14: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 60; Art. 2 amended Article 68; Art. 3 amended Article 92; Art. 4 amended Article 133; Art. 5 amended Article 136; Art. 6 amended Article 140; Art. 7 repealed-already-absent Article 154; Art. 8 amended Article 190; Art. 9 repealed-already-absent Article 233; Art. 10 repealed Article 236; Art. 11 amended Article 263.
- Law n° 059/2023: in force 2023-12-05 (Article 23: Entry into force comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 35; Art. 2 amended Article 60; Art. 3 amended Article 64; Art. 4 amended Article 84; Art. 5 amended Article 92; Art. 6 amended Article 99; Art. 7 amended Article 100; Art. 8 amended Article 108; Art. 9 amended Article 117; Art. 10 amended Article 120; Art. 11 amended Article 121; Art. 12 amended Article 123; Art. 13 inserted Article 132 bis; Art. 14 amended Article 133; Art. 15 amended Article 152; Art. 16 amended Article 172; Art. 17 amended Article 177; Art. 18 repealed-already-absent Article 218; Art. 19 inserted Article 262 bis; Art. 20 amended Article 271; Art. 21 amended Article 291.
- Law n° 059/2023: the English text prints no closing quotation mark after the restated text beginning 'Article 262 bis: Obstructing or preventing the enforcement o'; it ends with its article.
- Penal Code: in force 2018-09-27 (Article 335: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head "Official Gazette no. Special of 27/09/2018").
- Penal Code: no official consolidation exists (the portal serves the 2018 law and its two amending laws as separate Gazette texts), so the later versions are replays of the amending laws and of the two Supreme Court rulings. Each restated article is the amending law's own text, verbatim after normalisation.
- Penal Code: where an amending law restates only the body of an article, the article keeps the heading it had (Law 69/2019 Arts. 2-11 and Law 059/2023 Arts. 1-7, 9-11, 14, 15, 21 each carry a heading of their own, which is the amending article's heading, not a restated one).
- Court rulings: dated by the judgment day printed in the Rwanda Law Reports headnote (Re Mugisha "24 April 2019", Re Byansi "May 20, 2022"); each ruling ordered publication in the Official Gazette, which was not located, so the version takes effect on the judgment day. Struck or repealed articles are removed; Article 136 keeps paragraphs 1-2 and the Court's reframed paragraph 3 (RLR V.3-2019, English text, para. [132]).
- Penal Code: the 2018 table of contents misprints "Article 2826" for Article 286; the body is read from the second "Article One".
- Data protection: in force 2021-10-15 (Article 70: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). The portal lists no amending law. Article 67 gives controllers and processors already in operation two years from publication to conform; this is left in the text and not encoded in applies.
- Text: the English column only (extract.py: running heads removed by content, columns from the two gutters, paragraphs by line pitch). Normalised once: NBSP and soft hyphens, one form of quotes and apostrophes ("'), em dash to en dash, "Nº"/"n°" to "N°"/"n°", list ordinals "1 º" to "1°". Each file is "Article N: heading" as printed, then one paragraph per line.
- Enacting formula: each whole text's paragraphs between its table of contents and its first article (or its PREAMBLE) are the unit enacting-formula: title, promulgation formula and the Parliament's sittings and citations. Trailing PART/TITLE headings (Law 68/2018) are left out, like CHAPTER/Section/Subsection headings. An amending law does not change the amended act's enacting formula; the 2023 revision replaces the Constitution's.
- Every text has a PDF text layer (checked with PyMuPDF); no OCR is used anywhere.
- Sources: the API metadata and the PDFs; robots.txt of amategeko.gov.rw allows all agents. No Wayback capture was needed.
- Public servants statute: in force 2020-10-08 (Article 93: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head "Official Gazette n° Special of 08/10/2020").
- Law n° 019/2020: in force 2020-11-20 (Article 3: Commencement comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 inserted Article 21 bis.
- Law n° 019/2020: its commencement article also says "It takes effects as of 8 October 2020"; the version takes the in-force (publication) day and its note records the retroactive effect.
- Law n° 019/2020: the restated text beginning 'Article 21 bis: Maternity leave' ends with the closing quotation mark printed before the full stop; the mark is removed and the full stop kept.
- Law n° 052/2024: in force 2024-06-19 (Article 9: Entry into force comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 9; Art. 2 amended Article 21; Art. 3 amended Article 21 bis; Art. 4 repealed Article 22; Art. 5 repealed Article 23; Art. 6 repealed Article 24; Art. 7 repealed Article 25.
- Law n° 017/2026: in force 2026-04-24 (Article 4: Entry into force comes into force on the date of its publication in the Official Gazette of the Republic of Rwanda; Gazette running head). Replayed: Art. 1 amended Article 3; Art. 2 amended Article 4.
- Public servants statute: no official consolidation exists (the portal serves Law n° 017/2020 and its three amending laws as separate Gazette texts), so the later versions are replays of the amending laws: each restated or inserted article is the amending law's own text, verbatim after normalisation. Where an amending law restates only the body of an article (Law n° 052/2024 Art. 1 for Article 9; Law n° 052/2024 Art. 2 for Article 21; Law n° 017/2026 Art. 1 for Article 3; Law n° 017/2026 Art. 2 for Article 4), the article keeps its heading as enacted (the amending article's own heading is not part of the restated text).
- Public servants statute: the folder was law-2020-017/ in the earlier Lexifina build of this repository (main 121603e, its own tools); it is public-servants/ here, with the same article files.

## What AI did and did not do

The fetch, parse and check scripts were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above, through code that anyone can rerun.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- Claude Code (Claude Opus 5.5, claude-opus-5-5) wrote fetch.py, extract.py changes and parse.py and chose the sources. No model reads or writes legal text: every unit is extracted by code from the PDF text layer. 0 model calls at data-build time.
