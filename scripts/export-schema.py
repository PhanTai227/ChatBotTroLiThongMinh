"""Sinh lại schema.sql từ các file migration trong backend/app/migrations.

Migration mới là nguồn sự thật duy nhất của lược đồ. Tệp schema.sql ở thư mục gốc
chỉ là bản sao để đọc và đối chiếu, tuyệt đối không sửa tay.

Cách dùng:  python scripts/export-schema.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "backend" / "app" / "migrations"
TARGET = ROOT / "schema.sql"

HEADER = f"""-- LƯỢC ĐỒ CƠ SỞ DỮ LIỆU - HỆ THỐNG MINDORA
-- Tệp này được SINH TỰ ĐỘNG từ backend/app/migrations, không được sửa tay.
-- Sinh lại bằng lệnh: python scripts/export-schema.py
-- Ngày sinh: {date.today().isoformat()}
--
-- Quyết định thiết kế: khoá chính dùng INTEGER AUTOINCREMENT thay vì UUID TEXT để
-- giữ nguyên dữ liệu đang có và thuận tiện chuyển sang PostgreSQL sau này.
-- Ràng buộc CHECK/UNIQUE được đặt ở tầng cơ sở dữ liệu để dữ liệu luôn hợp lệ.
"""


def build() -> str:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        raise SystemExit(f"Không tìm thấy file migration trong {MIGRATIONS_DIR}")
    blocks = [HEADER]
    for path in files:
        body = path.read_text(encoding="utf-8").strip()
        blocks.append(f"-- ============ {path.stem} ===========\n{body}")
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    TARGET.write_text(build(), encoding="utf-8")
    print(f"Da cap nhat {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
