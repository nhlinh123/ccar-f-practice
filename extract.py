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

OPT_CONTENT = re.compile(r'<div class="practice-option-content[^"]*">(.*?)</div>', re.S)


def options_of(block, qid):
    """[(letter, inner_html)] in source A..F order."""
    labelled = re.findall(r'<label for="answer-%s-([A-F])"[^>]*>(.*?)</label>' % re.escape(qid), block, re.S)
    if labelled:
        out = []
        for letter, inner in labelled:
            m = OPT_CONTENT.search(inner)
            out.append((letter, m.group(1) if m else inner))
        return sorted(out)
    legacy = re.findall(r'<label for="answer-\d+-([A-F])".*?<div class="practice-option-content">(.*?)</div>', block, re.S)
    return sorted(legacy)


def explanation_of(block):
    """Explanation HTML; each block carries a <template> duplicate, so take the first match."""
    m = re.search(r'<div class="practice-explanation-content[^"]*">(.*?)</div>\s*</section>', block, re.S)
    if m:
        return m.group(1)
    m = re.search(r'<div class="practice-explanation-content[^"]*">(.*?)</div>', block, re.S)
    return m.group(1) if m else ''


def correct_keys(block, letters):
    """Letters of the correct option(s), supporting single and multiple-response markup."""
    for attr in KEY_ATTRS:
        found = re.findall(rf'{attr}="([^"]*)"', block)
        if found:
            keys = []
            for chunk in found:
                for c in re.findall(r'[A-F]', chunk.upper()):
                    if c not in keys:
                        keys.append(c)
            if keys:
                return keys, attr
    marked = re.findall(r'<label for="answer-\d+-([A-F])"[^>]*data-answer-result="correct"', block)
    if marked:
        return sorted(set(marked)), 'label data-answer-result'
    checked = re.findall(r'<input[^>]*id="answer-\d+-([A-F])"[^>]*checked', block)
    if checked:
        return sorted(set(checked)), 'checked input'
    return [], 'none'


def stated_keys(expl):
    """Letters the explanation's answer section lists — used to cross-check the site key."""
    m = re.search(r'(?:3\. Đáp án|Giải thích)</h[34]>(.*?)(?=<h[34]|</section>)', expl, re.S)
    if not m:
        return []
    letters = []
    for lm in re.finditer(r'(?:<li>|<p>|<strong>)\s*(?:<p>|<strong>)?\s*([A-F])[.)]', m.group(1)):
        if lm.group(1) not in letters:
            letters.append(lm.group(1))
    return letters[:6]


# key-fix: source keys only A on these multi-select items
FIXES = {
    '1350': ('AB', 'Hai nhu cầu cần hai cơ chế khác nhau. Context editing tự xóa kết quả tool cũ khi hội thoại gần ngưỡng token, giải quyết áp lực context trong phiên. Memory tool cho Claude lưu và truy hồi thông tin qua các hội thoại riêng biệt, đáp ứng nhu cầu nhớ sự kiện dự án qua nhiều ngày.'),
    '1351': ('AC', 'Orchestrator-workers để một LLM trung tâm xác định và giao subtask lúc chạy sau khi xem đầu vào, nên hợp với tác vụ có subtask thay đổi khó đoán theo từng trường hợp. Sectioning chia sẵn thành các subtask đã biết rồi chạy song song, nên hợp với tác vụ tách được rõ ràng. Cả phát biểu về thời điểm phân rã lẫn phát biểu về loại tác vụ phù hợp đều đúng.'),
    '1353': ('AB', 'Server-side fallback giúp request bị từ chối vẫn có phản hồi kịp thời trong cùng lời gọi API. Chọn model có độ trễ thấp như Claude Haiku 4.5 cho luồng triage trực tiếp giúp đạt p95 dưới 2 giây. Vẫn cần đo p95 trên tải thật; fallback cho refusal không thay được kế hoạch xử lý mất dịch vụ.'),
    '1356': ('ABC', 'Ba lớp phòng vệ bổ sung cho nhau. Chính sách trong system prompt coi nội dung tool trả về là dữ liệu không đáng tin, không được ghi đè system prompt hay yêu cầu gốc. JSON-encode nội dung email giữ ranh giới cấu trúc để dấu nháy hoặc thẻ không phá vỡ khối bao quanh. Classifier nhẹ sàng lọc tool output trước khi tới agent chính để loại bỏ hoặc gắn cờ nội dung nghi injection. Không lớp nào một mình chặn được mọi prompt injection.'),
    '1366': ('ABC', 'Ba cơ chế cùng giúp phiên dài tiếp tục mà không mất trạng thái quan trọng. Server-side compaction tự tóm tắt các lượt cũ khi gần giới hạn context. Context editing xóa kết quả tool cũ theo ngưỡng token và giữ các cặp tool use/result gần nhất. Memory tool lưu trạng thái quan trọng ra nơi lưu bền vững trước khi context cũ bị dọn, để phiên phục hồi nhanh.'),
    '1370': ('ABC', 'Ba quan sát đều là bằng chứng model thiếu năng lực: độ chính xác trên subtask reasoning nhiều bước vẫn dưới ngưỡng dù đã sửa prompt; workflow cần hiểu sâu qua chuỗi bước phụ thuộc nhau, nơi lỗi nhỏ cộng dồn; review thủ công xác nhận lỗi là lỗi reasoning thật chứ không do input thiếu hoặc bị cắt. Chi phí, timeout mạng hay prompt chưa thích nghi là vấn đề khác, không chứng minh mismatch.'),
    '1373': ('ABC', 'Ba biện pháp xử lý trực tiếp thiên lệch, công bằng và minh bạch. Paired-scenario evaluation giữ nguyên nội dung hiệu suất và so sánh tone, mức chi tiết giữa các nhóm nhân viên để phát hiện thiên lệch. Ghi lại các yếu tố mà assistant được hướng dẫn cân nhắc giúp reviewer kiểm tra được. Cho mọi nhân viên cơ chế hỏi các yếu tố đã định hình bản tóm tắt của mình đáp ứng yêu cầu minh bạch.'),
    '1374': ('ABC', 'Hướng dẫn chọn model của Anthropic nêu ba tiêu chí chính: năng lực model cần có để đáp ứng nhu cầu, tốc độ phản hồi mà ứng dụng yêu cầu, và ngân sách cho phát triển lẫn vận hành. Buổi discovery cần xác định đủ cả ba trước khi đề xuất model.'),
    '1380': ('ABC', 'Mỗi yêu cầu khớp một cơ chế. Claude for Teams hoặc Enterprise cho Claude Code và claude.ai dùng chung gói theo seat, không phải vận hành hạ tầng. Server-managed settings phân phối từ admin console của claude.ai tới cả session local lẫn web mà không cần MDM. Dashboard claude.ai/analytics/claude-code cho cái nhìn tập trung về mức dùng trên gói Teams và Enterprise.'),
}

# key-fix: statements the source only had as an image
Q_EXTRA = {
    '956': '<ol><li>Authentication and authorization run before retrieval so retrieval can filter by identity.</li>'
           '<li>An asynchronous queue absorbs bursty traffic between intake and the model invocation layer.</li>'
           '<li>Tax computation is encoded directly in the system prompt rather than in code.</li>'
           '<li>Conversation logs include unredacted government identifiers to maximize signal for tuning.</li></ol>',
}


def fix_explanation(expl, right, why, note):
    """Rewrite a cleaned explanation for a corrected key: header, main paragraph, wrong-option list, review note."""
    expl = re.sub(r'<p><strong>Nội dung đáp án theo khóa nguồn:</strong>.*?</p>\s*<p>.*?</p>',
                  f'<p><strong>Nội dung đáp án (khóa đã sửa):</strong> {"; ".join(right)}</p><p>{why}</p>', expl, count=1, flags=re.S)
    expl = re.sub(r'<li><strong>(.*?)</strong>:.*?</li>', lambda m: '' if m.group(1) in right else m.group(0), expl)
    return re.sub(r'<p><strong>Cần xem lại:</strong>.*?</p>', f'<p><strong>Đã sửa:</strong> {note}</p>', expl, count=1, flags=re.S)


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
        opts = options_of(b, qid)
        letters = [L for L, _ in opts]
        keys, how = correct_keys(b, letters)
        expl = explanation_of(b)

        # Some items are multiple-response ("chọn nhiều đáp án"): the page marks more than one option.
        if len(keys) > 1:
            notes_multi.append(qid)

        # The site key is occasionally wrong; when the explanation states its answer letter, trust it.
        stated = [k for k in stated_keys(expl) if k in letters]
        if stated and set(stated) != set(keys):
            notes.append(f'id {qid}: site key {"/".join(keys)} -> explanation says {"/".join(stated)}')
            keys = stated

        fix = FIXES.get(qid)
        if fix:
            notes.append(f'id {qid}: source key {"/".join(keys)} -> {"/".join(fix[0])} (FIXES)')
            note = f'khóa nguồn chỉ có {"/".join(keys)} dù đề yêu cầu chọn nhiều đáp án; đã sửa thành {"/".join(fix[0])}.'
            keys = list(fix[0])

        missing = [k for k in keys if k not in letters]
        if missing or not keys:
            notes.append(f'id {qid}: skipped (correct letters {keys or "none"} not among options {letters})')
            continue

        expl = clean(expl)
        if fix:
            right = [unwrap_p(clean(o)) for L, o in opts if L in keys]
            expl = fix_explanation(expl, right, fix[1], note)
        # Some banks cite options by letter ("<p>C. ", "(C)"); mark them so the app can relabel.
        expl = re.sub(r'(<p>|<strong>)([A-F])\.', r'\1{{\2}}.', expl)
        expl = re.sub(r'\(([A-F])\)', r'({{\1}})', expl)

        row = {
            'id': qid,
            'q': unwrap_p(clean(q)) + Q_EXTRA.get(qid, ''),
            'options': [unwrap_p(clean(o)) for _, o in opts],  # source A, B, C ... order
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
    maxopt = max((len(r['options']) for r in qs), default=4)
    print(f'  correct-letter spread: {[sum(1 for r in qs if i in ans_of(r)) for i in range(maxopt)]}')
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
