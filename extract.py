"""Extract the CCAR-P question bank from a saved CertLand practice page into questions.js.

Usage:
    python extract.py ccar-p-all.html [-o questions.js]

The saved page must be the *full* HTML (a few hundred KB). Each question sits in a
<details class="qblock"> block with its options and explanation, which is what this
script parses. It preserves the original A/B/C/D order and records the correct
answer as an index, so the app can shuffle options and still relabel the letters
inside explanations.

Explanation text keeps the original option letters as {{X}} placeholders:
"{{C}}. ..." means "the option that was originally C" — the app rewrites it to
whatever letter that option shows at after shuffling.
"""
import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser

ALLOWED = {'p', 'code', 'strong', 'em', 'ul', 'ol', 'li', 'h4', 'a', 'br', 'pre', 'blockquote'}


class Clean(HTMLParser):
    """Keep only an allowlist of tags; drop all attributes except https hrefs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            return
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if not href.startswith('https://'):
                return
            self.out.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener">')
        else:
            self.out.append(f'<{tag}>')

    def handle_endtag(self, tag):
        if tag in ALLOWED and tag != 'br':
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        self.out.append(html.escape(data.replace('\\"', '"'), quote=False))


def clean(s):
    c = Clean()
    c.feed(s)
    out = re.sub(r'\s+', ' ', ''.join(c.out)).strip()
    return re.sub(r'`([^`<]+)`', r'<code>\1</code>', out)


def unwrap_p(s):
    m = re.fullmatch(r'<p>(.*)</p>', s, re.S)
    return m.group(1) if m and '<p>' not in m.group(1) else s


def text_key(s):
    """Normalized question text, used to spot duplicates that differ only in markup."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', s))
    return re.sub(r'[^0-9a-zà-ỹ]+', ' ', t.lower()).strip()


KEY_ATTRS = ('data-correct-options', 'data-correct-answers', 'data-correct-option')


def correct_keys(block):
    """Return (letters, how) for the correct option(s) — single or multiple-response."""
    for attr in KEY_ATTRS:
        m = re.search(rf'{attr}="([^"]*)"', block)
        if m:
            letters = re.findall(r'[A-F]', m.group(1).upper())
            if letters:
                return letters, attr
    checked = re.findall(r'<input[^>]*id="answer-\d+-([A-F])"[^>]*checked', block)
    if checked:
        return checked, 'checked input'
    if re.search(r'<input[^>]*type="checkbox"', block):
        return [], 'checkbox'
    return [], 'none'


def stated_keys(expl):
    """Letters the explanation's "3. Đáp án" section lists — used to cross-check the site key."""
    m = re.search(r'3\. Đáp án</h4>(.*?)(?=<h4|</section>)', expl, re.S)
    if not m:
        return []
    letters = []
    for lm in re.finditer(r'(?:<li>|<p>|<strong>)\s*(?:<p>|<strong>)?\s*([A-F])[.)]', m.group(1)):
        if lm.group(1) not in letters:
            letters.append(lm.group(1))
    return letters[:4]


def ans_of(row):
    return row['answers'] if 'answers' in row else [row['answer']]


def parse(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    blocks = re.findall(r'<details class="qblock">.*?</details>', src, re.S)
    if not blocks:
        sys.exit(
            f'No <details class="qblock"> blocks found in {path} ({len(src):,} bytes).\n'
            'The saved page is probably incomplete or from a different layout.\n'
            'Re-save the full practice page and try again.'
        )

    rows, notes, notes_multi = [], [], []
    for b in blocks:
        qid = re.search(r'data-question-id="(\d+)"', b)
        qid = qid.group(1) if qid else str(len(rows) + 1)
        q = re.sub(r'<span class="qnum">.*?</span>', '', re.search(r'<summary>(.*?)</summary>', b, re.S).group(1))
        opts = sorted(re.findall(
            r'<label for="answer-\d+-([A-Z])".*?<div class="practice-option-content">(.*?)</div>', b, re.S))
        letters = [L for L, _ in opts]
        keys, how = correct_keys(b)
        m = re.search(r'<div class="practice-explanation-content">(.*?)</div>\s*</section>', b, re.S)
        expl = m.group(1) if m else ''

        # Some items are multiple-response ("select two"): the page then marks more than one option.
        if len(keys) > 1:
            notes_multi.append(qid)
        if 'checkbox' in how:
            notes.append(f'id {qid}: options use checkboxes ({how})')

        # The site key is occasionally wrong; when the explanation states its answer letter, trust it.
        stated = stated_keys(expl)
        if stated and set(stated) != set(keys):
            notes.append(f'id {qid}: site key {"/".join(keys)} -> explanation says {"/".join(stated)}')
            keys = stated

        missing = [k for k in keys if k not in letters]
        if missing or not keys:
            notes.append(f'id {qid}: skipped (correct letters {keys or "none"} not among options {letters})')
            continue

        expl = clean(expl)
        # Explanations cite options by original letter ("<p>C. ", "(C)"); mark them so the app can relabel.
        expl = re.sub(r'(<p>|<strong>)([A-D])\.', r'\1{{\2}}.', expl)
        expl = re.sub(r'\(([A-D])\)', r'({{\1}})', expl)

        row = {
            'id': qid,
            'q': unwrap_p(clean(q)),
            'options': [unwrap_p(clean(o)) for _, o in opts],  # original A, B, C, D order
            'explanation': expl,
        }
        answers = sorted(letters.index(k) for k in keys)
        if len(answers) == 1:
            row['answer'] = answers[0]
        else:
            row['answers'] = answers  # multiple-response question
        rows.append(row)

    # Keep only distinct questions: the same scenario can appear twice in a bank dump.
    unique, seen = [], {}
    for r in rows:
        k = text_key(r['q'])
        if k in seen:
            prev = seen[k]
            why = 'same answer' if ans_of(prev) == ans_of(r) else \
                  f'CONFLICTING answer {ans_of(prev)} vs {ans_of(r)}'
            notes.append(f'id {r["id"]}: duplicate of id {prev["id"]} ({why}) -> dropped')
            continue
        seen[k] = r
        unique.append(r)

    report(unique, rows, len(blocks), notes, notes_multi)
    return unique


def report(qs, rows, blocks, notes, notes_multi=()):
    ids = [r['id'] for r in qs]
    multi = [r['id'] for r in qs if len(ans_of(r)) > 1]
    bad_opts = [r['id'] for r in qs if not 2 <= len(r['options']) <= 6]
    no_expl = [r['id'] for r in qs if not r['explanation']]
    out_of_range = [r['id'] for r in qs if any(not 0 <= a < len(r['options']) for a in ans_of(r))]
    print(f'{blocks} blocks -> {len(rows)} parsed -> {len(qs)} unique questions')
    print(f'  single-answer:      {len(qs) - len(multi)}')
    print(f'  multiple-response:  {len(multi)}' + (f'  (ids {", ".join(multi[:12])}{" ..." if len(multi) > 12 else ""})' if multi else ''))
    print(f'  duplicates dropped: {len(rows) - len(qs)}')
    print(f'  with explanation:   {len(qs) - len(no_expl)}')
    print(f'  option counts:      {sorted({len(r["options"]) for r in qs})}')
    for label, bad in (('bad option count', bad_opts), ('no explanation', no_expl), ('answer out of range', out_of_range)):
        if bad:
            print(f'  WARNING {label}: {", ".join(bad[:12])}{" ..." if len(bad) > 12 else ""}')
    if notes:
        print('\n'.join(notes))
    print(f'  correct-letter spread: {[sum(1 for r in qs if i in ans_of(r)) for i in range(4)]}')
    print(f'  first/last id: {ids[0] if ids else "-"} .. {ids[-1] if ids else "-"}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sources', nargs='+', help='saved practice page(s)')
    ap.add_argument('-o', '--out', default='questions.js')
    a = ap.parse_args()

    bank = []
    for src in a.sources:
        bank.extend(parse(src))

    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('// Generated by extract.py. answer = index of the correct option; '
                '{{X}} in explanation = original option letter X.\n')
        f.write('window.QUESTIONS = ' + json.dumps(bank, ensure_ascii=False, indent=1) + ';\n')
    print(f'\nwrote {len(bank)} questions to {a.out}')


if __name__ == '__main__':
    main()
