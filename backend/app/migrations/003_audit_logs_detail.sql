-- 003_audit_logs_detail: lưu thêm thông tin mô tả cho dòng nhật ký.
--
-- Khi một tài khoản bị xoá, không thể giữ khoá ngoại tới tài khoản đó (dòng nhật ký
-- phải tồn tại độc lập với vòng đời người dùng). Vì vậy thông tin định danh người
-- bị xoá được lưu ở cột detail dạng văn bản.

ALTER TABLE audit_logs ADD COLUMN detail TEXT;
