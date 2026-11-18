# CCAR-P · Aurora Practice

Ứng dụng luyện thi **Claude Certified Architect – Professional (CCAR-P)** chạy hoàn toàn offline trong trình duyệt — một file HTML + một file dữ liệu câu hỏi, không backend, không gửi dữ liệu đi đâu.

Bản này dựng lại đúng bộ tính năng của `cca-f_practice` nhưng với giao diện **Aurora Nebula 2.0**: nền tinh vân nhiều lớp, kính mờ sâu, ánh sáng theo con trỏ, thẻ nghiêng 3D, vòng điểm phát sáng và pháo hoa canvas khi đạt.

## Tính năng

- **Hai chế độ**: đề thi ngẫu nhiên (63 câu, đúng độ dài kỳ thi thật) và toàn bộ ngân hàng.
- **Trộn câu + trộn đáp án** mỗi lần bắt đầu; phần giải thích tự đổi chữ cái A/B/C/D theo thứ tự mới.
- **Chấm ngay**: đúng lên xanh + confetti, sai rung nhẹ + hiện giải thích.
- **Đồng hồ**, **điểm**, **chuỗi đúng liên tiếp** ngay trên đầu bài.
- **Kết quả**: vòng tròn phần trăm, đạt/chưa đạt mốc 80%, thống kê đúng/sai/chuỗi/thời gian, pháo hoa khi đạt.
- **Xem lại câu sai**: đáp án đúng, lựa chọn của bạn, giải thích đầy đủ.
- **Phím tắt**: `A`–`D` hoặc `1`–`4` chọn, `Enter` sang câu tiếp, `?` mở bảng phím tắt.
- **Cài đặt**: 4 giao diện (Aurora, Trắng đen, Đen trắng, Vàng đen), bật/tắt âm thanh, tắt toàn bộ hiệu ứng cho máy yếu. Lưu theo trình duyệt.

## Cấu trúc

```
index.html    toàn bộ UI + logic (không phụ thuộc thư viện ngoài)
questions.js  ngân hàng câu hỏi, sinh ra bởi extract.py
extract.py    bộ trích xuất từ trang practice đã lưu
```

## Tạo lại ngân hàng câu hỏi

Cần file HTML đầy đủ của trang luyện tập (vài trăm KB — bản lưu thiếu vài KB sẽ không có câu nào):

```bash
python extract.py ccar-p-all.html -o questions.js
```

Script in ra số câu, số câu có giải thích, phân bố đáp án và cảnh báo nếu có câu thiếu dữ liệu. Nếu file nguồn bị cắt, script báo ngay `No <details class="qblock"> blocks found`.

## Chạy thử

Mở thẳng `index.html`, hoặc phục vụ qua HTTP:

```bash
python -m http.server 8080
```

## Tuỳ chỉnh

Sửa `CFG` ở đầu khối script trong `index.html`:

```js
const CFG = { exam: 63, pass: 0.8 };   // số câu mỗi đề, tỉ lệ đạt
```

## Triển khai

Đưa `index.html`, `questions.js` lên GitHub Pages (Settings → Pages → Deploy from branch). Không cần build.
