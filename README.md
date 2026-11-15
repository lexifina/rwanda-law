# Rwanda: law history in git


The law of Rwanda as a git history: one file per article, one commit per version on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; picking a date gives the text in force that day.

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is Rwanda's national law, which global-law reads at `rwanda/national/acts/`.

**What is in it now:** six acts from the Official Gazette, with 12 versions from 23 January 2012 to 24 April 2026: the Constitution (its 2015 revision and its 2023 revision); Law n° 017/2020 establishing the general statute governing public servants, with its three amending laws (019/2020, 052/2024, 017/2026); Law n° 027/2019 relating to the criminal procedure, amended by Law n° 058/2023; Law n° 007/2021 governing companies, amended by Law n° 019/2023; Law n° 062/2024 governing evidence; and Law n° 45/2011 governing contracts. [`REPRODUCE.md`](REPRODUCE.md) and [`data/depth-versions.json`](data/depth-versions.json) name the Gazette file behind every version, with its SHA-256.

Each act is a folder with one file per article, one paragraph per line, plus `enacting-formula.md` (the title and enacting words): `law-2020-017/art-021-bis.md` is Article 21 bis of the public servants statute, on maternity and paternity leave; the Constitution is in `constitution/`, with its `preamble.md`.

The text is the English column of the trilingual Official Gazette (Kinyarwanda, English, French), read from each PDF's own text layer, with no OCR. The Kinyarwanda and French texts are not part of this record.

## Questions as git commands

| Question | Command |
| --- | --- |
| Every change to Article 21 bis of the public servants statute | `git log -p --word-diff -- law-2020-017/art-021-bis.md` |
| Which law wrote each line of Article 21 bis? | `git blame law-2020-017/art-021-bis.md` |
| Every version of the public servants statute, with the day each took effect | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- law-2020-017` |
| Article 21 bis as in force on 1 January 2024 | `python tools/on_date.py 2024-01-01 law-2020-017 21bis` |

**Outside git**, we also host this record publicly, for free:

- **[Ask Claude about Rwandan law](https://global-law.lexifina.com/v1/try_claude?country=rwanda)**: opens Claude with a first question ready.
- **[Ask ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=rwanda)**: the same question in ChatGPT.
- **[Call the API in your browser](https://global-law.lexifina.com/v1/search_law?query=annual+leave&jurisdictions=rwanda)**: a search of Rwandan law for "annual leave", returned as JSON. See the [documentation here](https://lexifina.com/api/global-law).

Both assistants read the record through the free Global law connector (MCP, `https://global-law.lexifina.com/mcp`); the first time, the chat gives you the link that adds it. Ask in English.

**Host it yourself easily.** All it takes is git and Python, and the tools run on your machine:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add rwanda/national/acts
python3 tools/law.py show 2026-01-01 rwanda/national/acts/law-2020-017/art-021-bis.md
```

Opened in Claude Code, Cursor, VS Code or Codex, the clone also starts a local MCP server with the same tools ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Dates

Each commit is dated at noon, Africa/Kigali (UTC+2, no summer time), on the day the version took effect, and carries it in its `In-force:` trailer:

- every law here comes into force on the day it is published in the Official Gazette (the Constitution on promulgation and publication), as its own commencement article says; the day is the one the Gazette's running head prints ("Official Gazette n° Special of 24/04/2026"), and the commit records both (`Evidence:` or `In-force-basis:`);
- Law n° 019/2020 also says it "takes effects as of 8 October 2020", before it was published: its commit keeps the day it came into force, 20 November 2020, and records the earlier day in `Takes-effect:`;
- the six commits of the evidence, contracts, criminal procedure and companies laws were added after all the others: they carry the in-force day as author date, but their committer date, which `git log --before` reads, is 2026-10-28. Ask for a date with `tools/on_date.py`.

Each change is credited to the law that made it (`Law n° 052/2024`, at an address that cannot exist, `law-2024-052@amategeko.invalid`), and the first version of an act to the act as enacted. The Constitution's two versions are credited as wholes, to the 2015 revision and to the Revision of 2023, which restates and renumbers it: an `art-NNN.md` file can hold a different provision after 2023.

## How it is checked

- `tools/check_repo.py` rebuilds every version from the Gazette PDFs and compares each file, byte for byte, with the extraction of its official text; a word check compares each text with the words of the PDF column itself. It expects all 12 law commits, each with its recorded author, day and source SHA-256.
- An amending law is replayed only where its article is printed in one of three forms ("is amended as follows", "is inserted to read as follows", "is repealed"); any other wording stops the build, and articles the law does not name must stay byte-identical.
- Rebuilding from the cached sources gives the same commit hashes (`tools/build.py --verify-rebuild`), and `tools/test_repo.py` checks blame, the dated tool and `git log --follow` on amended articles (see [`REPRODUCE.md`](REPRODUCE.md)).

## What it does not show

- **Most Rwandan law.** Only these six acts: no other laws, no Presidential, Prime Minister's or Ministerial Orders, and no case law.
- **The Constitution before 2015.** The 2003 text and its amendments of 2003, 2005, 2008 and 2010 are on amategeko.gov.rw only as scans, with no checkable text layer.
- **Official consolidations.** The versions after an amending law are replayed from it, not checked against an official consolidation (none is published for the public servants statute); there, where an amending law restates only an article's body, the heading stays as enacted.
- **Every later amendment.** Only the amending laws named above are applied; whether the evidence, contracts, criminal procedure and companies laws have been amended otherwise has not been checked.
- **Changes within a line.** Each paragraph is one line, so blame credits a whole paragraph; use `git log -p --word-diff` for the words.

## Sources

| Source | Kind | Past versions | Notes |
| --- | --- | --- | --- |
| [amategeko.gov.rw](https://amategeko.gov.rw) (Rwanda Law Reform Commission) | Official Gazette PDFs, served through the Commission's open API | each law as published in the Gazette | The English column of 12 trilingual Gazette texts; each file's id and SHA-256 are in `REPRODUCE.md` and `data/depth-versions.json` |

## Licence

See [`LICENSE`](LICENSE). No licence is granted: amategeko.gov.rw's terms say the legislation on it is the property of the Rwanda Law Reform Commission (RLRC), and that its texts do not replace those published in the Official Gazette of the Republic of Rwanda, the authentic text; the reuse terms are unclear. The tools in `tools/` are by Lexifina.

No AI model wrote, translated or corrected legal text, and none runs when the history is built; the scripts and documentation were written with an AI model (see [`REPRODUCE.md`](REPRODUCE.md)).

## More

From [lexifina/global-law](https://github.com/lexifina/global-law):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): every feature, and what every corpus must support (`git blame`, `law.py`, the MCP tools)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): questions and answers · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proposing changes · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): the MCP server · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): how it was built · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): how current each corpus is · [Monitoring](https://github.com/lexifina/global-law/tree/main/monitoring): whether updates are running · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): how each official source is watched for changes
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): how fast the tools are, measured
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): charts and bridges across the world's law
- [Vulnerabilities](https://github.com/lexifina/global-law/tree/main/vulnerabilities): mistakes in legislation as published
