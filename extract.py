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


def parse(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    blocks = re.findall(r'<details class="qblock">.*?</details>', src, re.S)
    if not blocks:
        sys.exit(
            f'No <details class="qblock"> blocks found in {path} ({len(src):,} bytes).\n'
            'The saved page is probably incomplete or from a different layout.\n'
            'Re-save the full practice page and try again.'
        )

    rows, notes = [], []
    for b in blocks:
        qid = re.search(r'data-question-id="(\d+)"', b)
        qid = qid.group(1) if qid else str(len(rows) + 1)
        q = re.sub(r'<span class="qnum">.*?</span>', '', re.search(r'<summary>(.*?)</summary>', b, re.S).group(1))
        opts = sorted(re.findall(
            r'<label for="answer-\d+-([A-Z])".*?<div class="practice-option-content">(.*?)</div>', b, re.S))
        letters = [L for L, _ in opts]
        key = re.search(r'data-correct-option="([A-Z])"', b).group(1)
        m = re.search(r'<div class="practice-explanation-content">(.*?)</div>\s*</section>', b, re.S)
        expl = m.group(1) if m else ''

        # The site key is occasionally wrong; when the explanation states its answer letter, trust it.
        stated = re.search(r'3\. Đáp án</h4>\s*(?:<ul>\s*<li>)?\s*(?:<p>|<strong>)?\s*([A-D])\.', expl)
        if stated and stated.group(1) != key:
            notes.append(f'id {qid}: site key {key} -> explanation says {stated.group(1)}')
            key = stated.group(1)

        if key not in letters:
            notes.append(f'id {qid}: skipped (correct letter {key} not among options {letters})')
            continue

        expl = clean(expl)
        # Explanations cite options by original letter ("<p>C. ", "(C)"); mark them so the app can relabel.
        expl = re.sub(r'(<p>|<strong>)([A-D])\.', r'\1{{\2}}.', expl)
        expl = re.sub(r'\(([A-D])\)', r'({{\1}})', expl)

        rows.append({
            'id': qid,
            'q': unwrap_p(clean(q)),
            'options': [unwrap_p(clean(o)) for _, o in opts],  # original A, B, C, D order
            'answer': letters.index(key),
            'explanation': expl,
        })

    # Keep only distinct questions: the same scenario can appear twice in a bank dump.
    unique, seen = [], {}
    for r in rows:
        k = text_key(r['q'])
        if k in seen:
            prev = seen[k]
            why = 'same answer' if prev['answer'] == r['answer'] else \
                  f'CONFLICTING answer {prev["answer"]} vs {r["answer"]}'
            notes.append(f'id {r["id"]}: duplicate of id {prev["id"]} ({why}) -> dropped')
            continue
        seen[k] = r
        unique.append(r)

    report(unique, rows, len(blocks), notes)
    return unique


def report(qs, rows, blocks, notes):
    ids = [r['id'] for r in qs]
    bad_opts = [r['id'] for r in qs if not 2 <= len(r['options']) <= 6]
    no_expl = [r['id'] for r in qs if not r['explanation']]
    out_of_range = [r['id'] for r in qs if not 0 <= r['answer'] < len(r['options'])]
    print(f'{blocks} blocks -> {len(rows)} parsed -> {len(qs)} unique questions')
    print(f'  duplicates dropped: {len(rows) - len(qs)}')
    print(f'  with explanation:   {len(qs) - len(no_expl)}')
    print(f'  option counts:      {sorted({len(r["options"]) for r in qs})}')
    for label, bad in (('bad option count', bad_opts), ('no explanation', no_expl), ('answer out of range', out_of_range)):
        if bad:
            print(f'  WARNING {label}: {", ".join(bad[:12])}{" ..." if len(bad) > 12 else ""}')
    if notes:
        print('\n'.join(notes))
    print(f'  answer distribution: {[sum(1 for r in qs if r["answer"] == i) for i in range(4)]}')
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
