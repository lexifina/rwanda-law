"""Checks corpus.json against the official texts in .cache/ and writes verification.json. Reads only the cache.

    python -X utf8 verify.py

1. Column check, independent of extract.py's word grouping: for every whole text (both Constitutions, Law 68/2018,
   Law 058/2021) PyMuPDF's own text of the English column (get_text with a clip rectangle between the gutters) is
   split into words and aligned with the words of the act's files in that version. Every file word must be matched in
   order; the clip words left over must be only the table of contents, the enacting formula, headings of chapters
   and sections (not kept as files), the signature block and running heads.
2. Replay check: in the version of each amending law, every article it amends or inserts equals the law's own
   restated text (extract.py + parse.unquote), and every article it does not name is byte-identical to the version
   before.
3. Today's text: the last version of the Constitution equals the 2023 official text file by file; the last version
   of the data protection law equals the 2021 official text; the last version of the Penal Code is the 2018 text
   with exactly the articles named by the two amending laws and the two rulings changed.
"""
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract as X  # noqa: E402
import parse as P  # noqa: E402

WORD = re.compile(r'\S+')


def words(s: str) -> list:
    return WORD.findall(P.norm(s))


def states(act: dict) -> list:
    out, cur = [], {}
    for v in act['versions']:
        if 'units' in v:
            cur = dict(v['units'])
        else:
            cur = dict(cur)
            for k, u in v.get('changes', {}).items():
                cur.pop(k, None) if u is None else cur.__setitem__(k, u)
        out.append((v, cur))
    return out


def column_check(fid: int, units: dict) -> dict:
    doc, _ = P.pdf(fid)
    pages = [X.page_words(p) for p in doc]
    left, right = X.gutters(pages, int(doc[0].rect.width))
    clip_words = []
    import pymupdf
    for p in doc:
        r = pymupdf.Rect(left, 0, right, p.rect.height)
        t = p.get_text('text', clip=r)
        t = re.sub(r'Official Gazette (?:n°|no\.) Special of \d\d/\d\d/\d{4}', ' ', ' '.join(t.split()))
        clip_words += words(t)
    file_words = []
    for k in sorted(units, key=lambda k: (k != 'preamble', k)):
        file_words += words(units[k]['text'])
    sm = difflib.SequenceMatcher(None, clip_words, file_words, autojunk=False)
    unmatched_file = sum(j2 - j1 for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal')
    bad = [(' '.join(clip_words[i1:i2])[:120], ' '.join(file_words[j1:j2])[:120])
           for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal' and j2 > j1]
    from collections import Counter
    missing = Counter(file_words) - Counter(clip_words)
    return {'file': fid, 'clip_words': len(clip_words), 'file_words': len(file_words),
            'file_words_not_in_column': sum(missing.values()), 'missing': sorted(missing.items())[:20],
            'file_words_out_of_order': unmatched_file, 'examples': bad[:12]}


def main():
    c = json.loads((HERE / 'corpus.json').read_text(encoding='utf-8'))
    acts = {a['slug']: a for a in c['acts']}
    out = {'column': [], 'replay': [], 'today': {}}
    whole = {('constitution', 0): 5144, ('constitution', 1): 3939, ('penal-code', 0): 4119,
             ('data-protection', 0): 4116}
    for (slug, i), fid in whole.items():
        st = states(acts[slug])[i][1]
        out['column'].append({'act': slug, 'version': i, **column_check(fid, st)})

    # replay
    pc = states(acts['penal-code'])
    for idx, fid in ((2, 4115), (4, 4073)):
        prev, (v, cur) = pc[idx - 1][1], pc[idx]
        ch, ops, _ = P.replay(fid, prev)
        named = {k for _, k, _ in ops}
        diffs = [k for k in sorted(set(prev) | set(cur)) if prev.get(k) != cur.get(k)]
        ok_named = all(cur.get(k) == ch[k] for k in ch)
        untouched_ok = all(k in named for k in diffs)
        out['replay'].append({'law_file': fid, 'from': v['from'], 'named': sorted(named), 'changed': diffs,
                              'restated_equal': ok_named, 'only_named_changed': untouched_ok})

    # today
    con_last = states(acts['constitution'])[-1][1]
    c23, _, _ = P.read_whole(3939, preamble=True)
    dp_last = states(acts['data-protection'])[-1][1]
    dp, _, _ = P.read_whole(4116)
    pc0, pc_last = pc[0][1], pc[-1][1]
    touched = sorted(k for k in set(pc0) | set(pc_last) if pc0.get(k) != pc_last.get(k))
    named_all = set()
    for v, _ in pc[1:]:
        named_all |= set(v.get('changes', {}))
    out['today'] = {
        'constitution_equals_2023_official': con_last == c23, 'constitution_files': len(con_last),
        'data_protection_equals_2021_official': dp_last == dp, 'data_protection_files': len(dp_last),
        'penal_code_files': len(pc_last), 'penal_code_changed_since_2018': touched,
        'penal_code_changed_only_by_named_events': set(touched) <= named_all,
    }
    ok = (all(x['file_words_not_in_column'] == 0 for x in out['column'])
          and all(r['restated_equal'] and r['only_named_changed'] for r in out['replay'])
          and out['today']['constitution_equals_2023_official'] and out['today']['data_protection_equals_2021_official']
          and out['today']['penal_code_changed_only_by_named_events'])
    out['ok'] = ok
    (HERE / 'verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8',
                                            newline='\n')
    for x in out['column']:
        print(x['act'], x['version'], x['file'], 'file words', x['file_words'], 'not in column', x['file_words_not_in_column'],
              'out of order', x['file_words_out_of_order'], x['missing'][:5])
        for e in x['examples'][:6]:
            print('    clip:', e[0], '| file:', e[1])
    for r in out['replay']:
        print('replay', r['law_file'], r['from'], 'restated_equal', r['restated_equal'], 'only_named',
              r['only_named_changed'])
    print(json.dumps({k: v for k, v in out['today'].items() if k != 'penal_code_changed_since_2018'}))
    print('OK' if ok else 'PROBLEMS')


if __name__ == '__main__':
    main()
