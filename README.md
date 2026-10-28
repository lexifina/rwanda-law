# Rwandan law as git history (private)

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
| 2015-12-24 | `constitution/2015` | Constitution of 2003 revised in 2015 | constitution |
| 2020-10-08 | `law-2020-017/2020-017` | Law n° 017/2020 | law-2020-017 |
| 2020-11-20 | `law-2020-017/2020-019` | Law n° 019/2020 | law-2020-017 |
| 2023-08-04 | `constitution/2023` | Revision of 2023 of the Constitution | constitution |
| 2024-06-19 | `law-2020-017/2024-052` | Law n° 052/2024 | law-2020-017 |
| 2026-04-24 | `law-2020-017/2026-017` | Law n° 017/2026 | law-2020-017 |

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

> All the content of this website is divided into two categories: legislation in force in Rwanda including international treaties and agreements ratified or acceded to by Rwanda and abrogated laws are property of Rwanda Law Reform Commission (RLRC) while Law reports and judgments are property of the Judiciary. These two are the only institutions allowed to make changes and updates on different features of this website.
>
> The laws contained in this website, in any way, do not modify the authenticity of the texts of laws published in the Official Gazette of the Republic of Rwanda and therefore cannot replace them.

This repository is private. **Ask the Rwanda Law Reform Commission (RLRC) before publishing it.** The Official Gazette
is the authentic text.
