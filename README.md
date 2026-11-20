# CCAR-P · Aurora Practice

Ứng dụng luyện thi **Claude Certified Architect – Professional (CCAR-P)** chạy hoàn toàn offline trong trình duyệt — một file HTML + một file dữ liệu câu hỏi, không backend, không gửi dữ liệu đi đâu.

Ngân hàng hiện có **160 câu**: 102 câu một đáp án, 58 câu chọn nhiều đáp án (2–3 đáp án), mỗi câu 4–6 phương án, tất cả đều có giải thích.

Bản này dựng lại đúng bộ tính năng của `cca-f_practice` nhưng với giao diện **Aurora Nebula 2.0**: nền tinh vân nhiều lớp, kính mờ sâu, ánh sáng theo con trỏ, thẻ nghiêng 3D, vòng điểm phát sáng và pháo hoa canvas khi đạt.

## Tính năng

- **Hai chế độ**: đề thi ngẫu nhiên (60 câu, đúng độ dài kỳ thi thật) và toàn bộ ngân hàng.
- **Hai dạng câu hỏi**: một đáp án (chấm ngay khi bấm) và **chọn nhiều đáp án** (bấm chọn nhiều ô rồi "Chấm đáp án", đúng khi chọn đủ và không thừa).
- **Trộn câu + trộn đáp án** mỗi lần bắt đầu; phần giải thích tự đổi chữ cái A–F theo thứ tự mới. Riêng chế độ 160 câu có công tắc trộn ngay trang chủ (mặc định bật): tắt để đi đúng thứ tự gốc của ngân hàng, cả câu lẫn đáp án. Lựa chọn được lưu theo trình duyệt.
- **Chấm ngay**: đúng lên xanh + confetti, sai rung nhẹ + hiện giải thích.
- **Đồng hồ**, **điểm**, **chuỗi đúng liên tiếp** ngay trên đầu bài.
- **Kết quả**: vòng tròn phần trăm, đạt/chưa đạt mốc 80%, thống kê đúng/sai/chuỗi/thời gian, pháo hoa khi đạt.
- **Xem lại câu sai**: đáp án đúng, lựa chọn của bạn, giải thích đầy đủ.
- **Phím tắt**: `A`–`F` hoặc `1`–`6` chọn, `Enter` chấm / sang câu tiếp, `?` mở bảng phím tắt.
- **Cài đặt**: 4 giao diện (Aurora, Trắng đen, Đen trắng, Vàng đen), bật/tắt âm thanh, tắt toàn bộ hiệu ứng cho máy yếu. Lưu theo trình duyệt.

## Cấu trúc

```
index.html    toàn bộ UI + logic (không phụ thuộc thư viện ngoài)
questions.js  ngân hàng câu hỏi, sinh ra bởi extract.py
extract.py    bộ trích xuất từ trang practice đã lưu
meo.html      sổ tay mẹo học: luật vàng + mẹo từng câu theo chủ đề
tips.js       dữ liệu mẹo cho từng câu, khớp theo id câu hỏi
```

## Sổ tay mẹo (`meo.html`)

Mở từ nút **Mẹo học** ở trang chủ, hoặc link **Mẹo nhớ câu này** dưới phần giải thích của mỗi câu (mở thẳng thẻ `meo.html#q<id>`).

- 12 luật vàng, danh sách từ báo hiệu đáp án sai, cách ôn.
- 160 thẻ chia 9 chủ đề. Mỗi thẻ: tình huống tóm tắt, từ khoá, đáp án đúng (tiếng Anh, rút gọn), luật nhớ nhanh, bẫy hay gặp, đề gốc.
- Tìm kiếm, lọc theo chủ đề, chế độ **Tự kiểm tra** (ẩn đáp án), lọc câu **Cần xem lại**, đánh dấu **Đã thuộc** (lưu theo trình duyệt).
- Loại câu, nhãn "Cần xem lại" và khoá đáp án đọc từ `questions.js`. `tips.js` chỉ chứa phần mẹo viết tay, nên khi sửa khoá trong `extract.py` thì cập nhật mục cùng id trong `tips.js`.

## Tạo lại ngân hàng câu hỏi

Cần file HTML đầy đủ của trang luyện tập (vài trăm KB — bản lưu thiếu vài KB sẽ không có câu nào):

```bash
python extract.py "ccar-p-all (1).html" -o questions.js
```

Script in ra số câu, số câu một đáp án / nhiều đáp án, số câu trùng bị loại, số câu có giải thích và cảnh báo nếu có câu thiếu dữ liệu. Nếu file nguồn bị cắt, script báo ngay `No <details class="qblock"> blocks found`.

File nguồn có một số lỗi, được sửa tay trong `extract.py`: `FIXES` sửa khóa và giải thích của 9 câu chọn nhiều đáp án mà nguồn chỉ đánh dấu A; `Q_EXTRA` bổ sung phần đề nguồn chỉ có dạng ảnh (Câu 70). Chạy lại script sẽ áp dụng lại các sửa đổi này.

## Chạy thử

Mở thẳng `index.html`, hoặc phục vụ qua HTTP:

```bash
python -m http.server 8080
```

## Tuỳ chỉnh

Sửa `CFG` ở đầu khối script trong `index.html`:

```js
const CFG = { exam: 60, pass: 0.8 };   // số câu mỗi đề, tỉ lệ đạt
```

## Triển khai

Đưa `index.html`, `questions.js`, `meo.html`, `tips.js` lên GitHub Pages (Settings → Pages → Deploy from branch). Không cần build.
