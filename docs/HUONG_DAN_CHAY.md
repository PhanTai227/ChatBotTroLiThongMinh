# HƯỚNG DẪN CHẠY CHƯƠNG TRÌNH — MINDORA

> Trợ lý học tập AI chạy hoàn toàn trên máy cục bộ (Ollama + SQLite + Tesseract).
> Chỉ cần Internet **lần đầu** để tải model AI; sau đó chạy offline được.

---

## 1. Yêu cầu môi trường

| Phần mềm | Phiên bản đã kiểm chứng | Ghi chú |
|---|---|---|
| Ollama | 0.34.4 | Cài bản Windows cho user hiện tại (mặc định) |
| Python | 3.13.7 | Backend dùng môi trường ảo sẵn có `backend/.venv` |
| Node.js | 24.x (npm 11.x) | Frontend đã có sẵn `node_modules` |
| Tesseract OCR (portable) | có sẵn trong repo | `tools/tesseract/tesseract.exe`, không cần cài đặt |

Các thư mục **đã có sẵn**, không cần tải lại:

- `backend/.venv` — thư viện Python (FastAPI, Uvicorn, httpx…)
- `frontend/node_modules` — thư viện React/Vite
- `ollama-models` — kho model AI cục bộ (~2 GB, bị `.gitignore`)
- `backend/.env` — cấu hình máy cục bộ (bị `.gitignore`)

---

## 2. Cách chạy nhanh (khuyên dùng)

Mở PowerShell **tại thư mục gốc** `D:\TroLiThongMinh` và chạy:

```powershell
.\start-local.ps1
```

Script tự động:

1. Khởi động Ollama (`ollama serve`) nếu cổng 11434 chưa có ai nghe.
2. Khởi động Backend (Uvicorn) tại `http://127.0.0.1:8000`.
3. Khởi động Frontend (Vite) tại `http://127.0.0.1:5173`.

Chỉ chạy backend (bỏ frontend) khi cần:

```powershell
.\start-local.ps1 -SkipFrontend
```

### Địa chỉ sau khi chạy

| Dịch vụ | Địa chỉ | Kiểm tra nhanh |
|---|---|---|
| Giao diện web (Frontend) | http://127.0.0.1:5173 | Mở trình duyệt, thấy trang đăng nhập |
| API + tài liệu Swagger (Backend) | http://127.0.0.1:8000/docs | Mở trình duyệt, thấy danh sách endpoint |
| Máy chủ AI (Ollama) | http://127.0.0.1:11434 | `ollama list` phải thấy model (mục 5) |

### Đăng nhập lần đầu

Tài khoản **quản trị mặc định** được backend tự tạo khi cơ sở dữ liệu còn trống:

- Email: `admin@mindora.local`
- Mật khẩu: `Admin@123`

(Mặc định trong `backend/.env.example`: `DEFAULT_ADMIN_EMAIL`,
`DEFAULT_ADMIN_PASSWORD`. Đổi mật khẩu ngay sau khi đăng nhập lần đầu.)

---

## 3. Chạy từng bước thủ công

Dùng khi `start-local.ps1` báo lỗi, hoặc khi cần xem log trực tiếp từng dịch vụ.
Mở **3 cửa sổ PowerShell riêng**, mỗi cửa sổ một lệnh.

### Bước 1 — Khởi động Ollama (bắt buộc đầu tiên)

```powershell
$env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'
ollama serve
```

> Bắt buộc đặt `OLLAMA_MODELS` **trước** `ollama serve`.
> Kiểm tra lại trong cửa sổ mới bằng `echo $env:OLLAMA_MODELS`.

Kiểm tra (cửa sổ PowerShell khác):

```powershell
$env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'
ollama list
```

Phải thấy ít nhất `qwen2.5:3b`. Nếu danh sách **rỗng**, xem mục 7.1.

### Bước 2 — Khởi động Backend

```powershell
cd D:\TroLiThongMinh\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend tự động: chạy migration SQLite, tạo tài khoản admin mặc định (nếu DB trống),
khởi tạo thư mục lưu trữ (`app/storage`). Mở http://127.0.0.1:8000/docs để xác nhận.

### Bước 3 — Khởi động Frontend

```powershell
cd D:\TroLiThongMinh\frontend
npm run dev -- --host 127.0.0.1
```

Mở http://127.0.0.1:5173. Frontend gọi API qua địa chỉ cố định
`http://127.0.0.1:8000` (xem `frontend/src/lib/auth.ts` → `API_BASE`), nên backend
**phải** chạy ở đúng cổng 8000.

---

## 4. Model AI

### 4.1. Model đang dùng

| Mục đích | Model | Cấu hình trong `backend/.env` | Trạng thái |
|---|---|---|---|
| Trả lời hội thoại (LLM) | `qwen2.5:3b` | `OLLAMA_MODEL` | Đã có trong kho (~1,9 GB) |
| Vector tìm kiếm tài liệu (embedding, RAG) | `nomic-embed-text` | `EMBEDDING_MODEL` + `EMBEDDING_DIM=768` | **Chưa có — cần tải** |

### 4.2. Tải model embedding (làm 1 lần, cần mạng)

```powershell
$env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'
ollama pull nomic-embed-text
```

Nếu thiếu model này, các tính năng **upload tài liệu → hỏi đáp theo tài liệu (RAG)**
sẽ báo lỗi `embedding_model_missing`; còn chat tự do (không RAG) vẫn chạy bình thường.

### 4.3. Đổi model khác (tùy chọn)

1. Tải model mới, ví dụ: `ollama pull qwen2.5:7b`.
2. Sửa `backend/.env`: `OLLAMA_MODEL=qwen2.5:7b` (hoặc admin đổi trong trang quản trị,
   giá trị lưu ở `system_settings.ai_model`).
3. Khởi động lại backend.
4. Nếu đổi **model embedding** khác `nomic-embed-text`, phải sửa `EMBEDDING_DIM`
   cho khớp số chiều của model mới (ví dụ `bge-m3` → `1024`) và sinh lại vector cũ.

---

## 5. Tệp cấu hình `backend/.env`

Tệp này **không đẩy lên git**. Tạo mới bằng cách chép từ mẫu:

```powershell
Copy-Item backend\.env.example backend\.env
```

Các biến quan trọng (xem đầy đủ kèm chú thích trong `backend/.env.example`):

| Biến | Ý nghĩa | Giá trị mặc định |
|---|---|---|
| `OLLAMA_HOST` | Địa chỉ máy chủ AI | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Model trả lời hội thoại | `qwen2.5:3b` |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | Model + số chiều vector RAG | `nomic-embed-text` / `768` |
| `TESSERACT_CMD` / `TESSERACT_LANG` | Đường dẫn + ngôn ngữ OCR | `D:\TroLiThongMinh\tools\tesseract\tesseract.exe` / `vie+eng` |
| `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` | Tài khoản admin lần đầu | `admin@mindora.local` / `Admin@123` |
| `DATABASE_PATH` | File SQLite (tính từ `backend/app`) | `learning_assistant.db` |

> Sau khi sửa `.env` phải **khởi động lại backend** để nhận giá trị mới.

---

## 6. Kiểm thử và kiểm tra mã nguồn

Chạy từ thư mục `backend`:

```powershell
cd D:\TroLiThongMinh\backend
.\.venv\Scripts\python.exe -m pytest                  # toàn bộ test
.\.venv\Scripts\python.exe -m pytest tests/test_chat.py  # 1 file test
.\.venv\Scripts\python.exe -m ruff check .            # kiểm tra lỗi/quy ước
```

Danh sách test: `backend/tests/` (`test_auth`, `test_chat`, `test_rag`,
`test_documents`, `test_embeddings`, `test_admin`, …).

Build frontend để kiểm tra lỗi TypeScript:

```powershell
cd D:\TroLiThongMinh\frontend
npm run build
```

---

## 7. Xử lý sự cố thường gặp

### 7.1. `ollama list` trống dù kho `ollama-models` vẫn có dữ liệu

**Nguyên nhân:** ứng dụng khay hệ thống **"ollama app"** tự khởi động cùng Windows
và chiếm cổng 11434 **trước**, nhưng nó đọc kho mặc định (`%USERPROFILE%\.ollama`)
thay vì kho của dự án → tiến trình `ollama serve` khởi động sau không bind được cổng.

**Cách sửa:**

1. Chuột phải biểu tượng Ollama ở khay hệ thống → **Quit**.
2. Kiểm tra không còn tiến trình nào:
   ```powershell
   Get-Process ollama* -ErrorAction SilentlyContinue
   ```
   Nếu còn, tắt bằng: `Stop-Process -Name 'ollama*','ollama app' -Force`
3. Khởi động lại đúng kho:
   ```powershell
   $env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'
   ollama serve
   ```
4. Kiểm tra lại: `ollama list` phải thấy `qwen2.5:3b`.

### 7.2. Chat báo "không kết nối được máy chủ AI" (`llm_unavailable`)

- Ollama chưa chạy → làm bước 1 (mục 3).
- Sai `OLLAMA_HOST` trong `backend/.env` → phải là `http://127.0.0.1:11434`.

### 7.3. Hỏi theo tài liệu báo thiếu model embedding

Chưa tải `nomic-embed-text` → làm mục 4.2.

### 7.4. Cổng bị chiếm (8000 / 5173 / 11434)

```powershell
Get-NetTCPConnection -LocalPort 8000,5173,11434 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalPort, OwningProcess
```

Tìm tiến trình cũ (uvicorn/vite/ollama) và tắt đi rồi chạy lại, hoặc khởi động lại máy.

### 7.5. OCR không chạy / báo thiếu Tesseract

- Kiểm tra file `tools/tesseract/tesseract.exe` còn tồn tại.
- Kiểm tra `TESSERACT_CMD` trong `backend/.env` trỏ đúng đường dẫn đó.
- Thư mục `tools/` bị `.gitignore` — máy mới clone repo cần chép `tools/` sang.

### 7.6. Quên mật khẩu admin

Xóa file `backend/app/learning_assistant.db` rồi khởi động lại backend để tạo lại
admin mặc định. Lưu ý cách này **xóa toàn bộ dữ liệu** (tài khoản, tài liệu, hội thoại).

---

## 8. Tóm tắt lệnh trong 1 phút

```powershell
# Cửa sổ 1: AI
$env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'; ollama serve

# Cửa sổ 2: Backend
cd D:\TroLiThongMinh\backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Cửa sổ 3: Frontend
cd D:\TroLiThongMinh\frontend; npm run dev -- --host 127.0.0.1

# Mở trình duyệt: http://127.0.0.1:5173  (đăng nhập admin@mindora.local / Admin@123)
```

Tài liệu thiết kế hệ thống chi tiết: [`THIET_KE_HE_THONG.md`](./THIET_KE_HE_THONG.md).

