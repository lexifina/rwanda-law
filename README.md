# Rwanda: law history

This repository will hold the legislation of Rwanda (RW) as a history: one file per provision and one commit per law taking effect, dated by the day it took force, with the law that made each change as the commit author. It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `rw/` in the world tree.

**Status:** no law yet. This first commit records where the law of Rwanda can be read and what a build would need.

**Can it be built?** Past versions by date are online, but with no API or bulk download, so a build has to read the site page by page.

**This commit is a placeholder.** The first real build must replace this history from scratch and force-push. It must never append law commits on top of it: they are dated by when each law took effect, often decades earlier, so dates in `main` would run backwards and break every on-date lookup. Builders should refuse to append when the root commit is this placeholder (its subject ends "sources, before any law").

**Official sources**

- [Official Gazette; RwandaLII](https://www.minijust.gov.rw/official-gazette): RwandaLII uses the Laws.Africa platform.

All sources, with their status, are in [SOURCES.md](SOURCES.md). How these files were made is in [REPRODUCE.md](REPRODUCE.md).

This repository describes sources; it is not legal advice and holds no legal text yet.
