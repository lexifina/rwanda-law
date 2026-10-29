# Rwanda: law history in git (private)

The law of Rwanda as a git history: one file per article, one commit per law or court ruling on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; `tools/on.py` gives the text in force on any day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `rw/`. Every text is the English column of the trilingual Official Gazette of the Republic of Rwanda (Kinyarwanda, English, French), as served by the Rwanda Law Reform Commission at [amategeko.gov.rw](https://amategeko.gov.rw), read from the PDF's own text layer.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitution/` | The Constitution of the Republic of Rwanda | 2 | 2015-12-24 to 2023-08-04 |
| `penal-code/` | Law n° 68/2018 of 30/08/2018 determining offences and penalties in general | 5 | 2018-09-27 to 2023-12-05 |
| `data-protection/` | Law n° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy | 1 | 2021-10-15 |
| `public-servants/` | Law n° 017/2020 of 07/10/2020 establishing the general statute governing public servants | 4 | 2020-10-08 to 2026-04-24 |

**Constitution**

| In force | Author |
| --- | --- |
| 2015-12-24 | Constitution of 2003 revised in 2015 (Official Gazette n° Special of 24/12/2015) |
| 2023-08-04 | Revision of the Constitution (2023) (Official Gazette n° Special of 04/08/2023), a whole-text restatement |

**Penal Code**

| In force | Author |
| --- | --- |
| 2018-09-27 | Law n° 68/2018 (as enacted) |
| 2019-04-24 | Re Mugisha, Supreme Court (Article 136 reframed in part, Articles 154 and 233 struck out) |
| 2019-11-29 | Law n° 69/2019 |
| 2022-05-20 | Re Byansi, Supreme Court (Article 218 devoid of effects) |
| 2023-12-05 | Law n° 059/2023 |

**Data protection**

| In force | Author |
| --- | --- |
| 2021-10-15 | Law n° 058/2021 (as enacted; no amending law is listed) |

**Public servants statute**

| In force | Author |
| --- | --- |
| 2020-10-08 | Law n° 017/2020 (as enacted) |
| 2020-11-20 | Law n° 019/2020 (inserts Article 21 bis; the law says it "takes effects as of 8 October 2020") |
| 2024-06-19 | Law n° 052/2024 (Articles 9, 21 and 21 bis restated; Articles 22 to 25 repealed) |
| 2026-04-24 | Law n° 017/2026 (Articles 3 and 4 restated) |

Each folder's `README.md` lists every article, how often it changed and when.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did Article 136 of the Penal Code say on 1 January 2019? | `python tools/on.py 2019-01-01 penal-code art-136` |
| The same, with raw git (bash) | `git show $(git rev-list -1 --before="2019-01-01T23:59:59Z" main -- penal-code/art-136.md):penal-code/art-136.md` |
| The same, in PowerShell | `$r = git rev-list -1 --before="2019-01-01T23:59:59Z" main -- penal-code/art-136.md; git show "$($r):penal-code/art-136.md"` |
| Which law wrote each line? | `git blame penal-code/art-136.md` |
| Every change, word by word | `git log -p --word-diff penal-code/art-136.md` |
| Every law in the record, in order | `git log --reverse --format="%ad %an" --date=short main` |
| Everything one law changed | `git show law/<key>` (tags `law/<key>` mark each law's commit) |
| The whole act on a date | `python tools/on.py 2020-01-01 penal-code` |
| Which law gave an article its wording on a date | `python tools/on.py --law 2020-01-01 penal-code art-060` |

After a rebuild, refresh tags with `git fetch --force --tags`: a plain fetch keeps stale tags.

## Dates

- Each commit is dated at **noon, Africa/Kigali, on the day the change took effect**. The day is also in the `In-force:` trailer, which the tools read.
- **Every law used here says it comes into force on its publication in the Official Gazette** (for example the Penal Code's Article 335, the data protection law's Article 70, the Constitution's Article 177 of 2015 and Article 176 of 2023, which also require promulgation). The day is the Gazette's own running head ("Official Gazette n° Special of DD/MM/YYYY").
- **Law n° 019/2020** comes into force on its publication (20 November 2020) but says "It takes effects as of 8 October 2020", the day Law n° 017/2020 came into force. Its commit is dated 20 November 2020; the earlier effect is stated in the commit message, not backdated.
- **Court rulings** are dated by the judgment day printed in the Rwanda Law Reports (Re Mugisha, 24 April 2019; Re Byansi, 20 May 2022). Each ruling ordered publication in the Official Gazette, which was not located.
- `--before="YYYY-MM-DD"` alone uses your clock's time of day, so a law that took effect that day may be missed before noon. Use `T23:59:59Z` as above, or the tool.

## How it is checked

- Every version is read back from git on the day it took effect and on the day before (`tools/check_repo.py`); both must match `corpus.json`. Results are in `REPRODUCE.md`.
- **Column check:** for each whole text, the words of every file are matched, in order, against PyMuPDF's own text of the English column (lines put in reading order by position), independently of the extractor's word grouping. Every word of every file is found, in order.
- **Replay check (Penal Code and public servants statute):** in each amending law's version, every article it amends or inserts equals the law's own restated text, and every article it does not name is byte-identical to the version before.
- **Today's text:** the last version of the Constitution equals the 2023 official text file by file; the data protection law equals its 2021 official text; the Penal Code is the 2018 text with exactly the articles named by the two amending laws and the two rulings changed; the public servants statute is the 2020 text with exactly the articles named by its three amending laws changed.
- The repository is rebuilt from the same data a second time and must give identical hashes.

## What "author" means

The author of a commit is the law (or ruling) that made the change, with an e-mail address that cannot exist (`...@amategeko.invalid`), so `git blame` and `git log --author` name laws. The committer is always Lexifina.

- **Credits come from the texts themselves.** An amending law names each article it amends, inserts or repeals; a ruling names the articles it strikes or reframes. Nothing is credited by guesswork.
- **The 2023 revision of the Constitution** restates and renumbers the whole Constitution (177 articles become 176), so it is one whole-text commit, and a file `art-NNN.md` can hold a different provision after 2023.
- Blame credits whole lines (one paragraph per line). Use `git log -p --word-diff` to see exactly which words each change made.

## What it does not show

- **The Constitution before the 2015 revision.** The 2003 Constitution is on amategeko.gov.rw only as an image scan, and amendment no. 1 of 2003 only with a machine OCR layer; no OCR is used, so they are left out. The 2005, 2008 and 2010 amendments have text but cannot be replayed without the 2003 base.
- **An official consolidation of the Penal Code or of the public servants statute.** None is published; their later versions are replays of the amending laws (and, for the Penal Code, the rulings), checked as above. Where an amending law restates only the body of an article, the article keeps its heading as enacted (so Article 21 of the statute keeps "Incidental leave", although Law n° 052/2024 heads its amending article "Circumstantial leave").
- **Kinyarwanda and French.** Kinyarwanda is the language the laws were drafted and adopted in; all three columns are official. This record is the English column only.
- **Headings above the article** (Part, Title, Chapter, Section, Subsection) are left out; each article file starts with "Article N: heading" as printed. Each act's `enacting-formula.md` holds the text before Article One (title, promulgation formula, the Parliament's sittings and citations), and the Constitution's `preamble.md` its preamble.
- **Instruments made under these laws** (Presidential, Prime Minister's and Ministerial Orders), and every other act.

## How it is built

From the cached Gazette PDFs, by deterministic code (`tools/fetch.py`, `tools/extract.py`, `tools/parse.py`, `tools/verify.py`) into `corpus.json`, then into git by the shared builder (`tools/build.py`). See REPRODUCE.md. No model reads or writes legal text.

## Licence and terms

There is no licence. amategeko.gov.rw says:

> All the content of this website is divided into two categories: legislation in force in Rwanda including international treaties and agreements ratified or acceded to by Rwanda and abrogated laws are property of Rwanda Law Reform Commission (RLRC) while Law reports and judgments are property of the Judiciary. These two are the only institutions allowed to make changes and updates on different features of this website.
>
> The laws contained in this website, in any way, do not modify the authenticity of the texts of laws published in the Official Gazette of the Republic of Rwanda and therefore cannot replace them.

This repository is private. **Ask the Rwanda Law Reform Commission (RLRC) before publishing it.** The Official Gazette is the authentic text. This is not legal advice.

## En français

Ce dépôt (privé) retrace l'historique de quatre textes rwandais : la Constitution (depuis la révision de 2015), la loi n° 68/2018 portant infractions et peines en général, la loi n° 058/2021 relative à la protection des données à caractère personnel et de la vie privée, et la loi n° 017/2020 portant statut général régissant les agents de l'État, avec ses trois lois modificatives. Un fichier par article, un commit par loi ou arrêt à la date de son entrée en vigueur, la loi étant l'auteur du commit. Les textes sont la colonne anglaise du Journal officiel trilingue, lue dans la couche texte des PDF publiés sur amategeko.gov.rw (sans OCR). Le Journal officiel fait seul foi.
