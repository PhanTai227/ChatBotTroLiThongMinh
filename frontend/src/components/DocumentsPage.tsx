import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Check,
  ChevronDown,
  Clock3,
  FileImage,
  FileText,
  Filter,
  Grid2X2,
  List,
  Loader2,
  Plus,
  Search,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import {
  apiRequest,
  apiUpload,
  formatFileSize,
  type DocumentItem,
  type DocumentListResponse,
  type DocumentStatusResponse,
} from '../lib/auth';
import { StatCard } from './DashboardCards';

type FileType = 'PDF' | 'DOCX' | 'XLSX' | 'Ảnh';
type ViewStyle = 'Sẵn sàng' | 'Đang xử lý' | 'Lỗi';

const ACCEPTED = '.pdf,.docx,.xlsx,.png,.jpg,.jpeg';

/** Các trạng thái đang xử lý nền, giao diện hiển thị gộp thành "Đang xử lý". */
const PROCESSING_STATUSES: DocumentItem['status'][] = ['uploading', 'ocr_processing', 'embedding'];

const TYPE_LABEL: Record<DocumentItem['file_type'], FileType> = {
  pdf: 'PDF',
  docx: 'DOCX',
  xlsx: 'XLSX',
  image: 'Ảnh',
};

const typeStyle: Record<FileType, string> = {
  PDF: 'bg-rose-50 text-rose-700',
  DOCX: 'bg-sky-50 text-sky-700',
  XLSX: 'bg-emerald-50 text-emerald-700',
  'Ảnh': 'bg-accent-soft text-accent',
};

function FileBadge({ type }: { type: FileType }) {
  return <div className={`grid size-11 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${typeStyle[type]}`}>{type === 'Ảnh' ? <FileImage size={19} /> : type}</div>;
}

function viewStyle(status: DocumentItem['status']): ViewStyle {
  if (status === 'ready') return 'Sẵn sàng';
  if (status === 'error') return 'Lỗi';
  return 'Đang xử lý';
}

function statusStyle(status: DocumentItem['status']) {
  const style = viewStyle(status);
  if (style === 'Sẵn sàng') return 'bg-emerald-50 text-emerald-700';
  if (style === 'Lỗi') return 'bg-rose-50 text-rose-700';
  return 'bg-amber-50 text-amber-700';
}

/** Tiến độ hiển thị cho thanh trạng thái. */
function progressOf(status: DocumentItem['status']): number {
  if (status === 'ready') return 100;
  if (status === 'error') return 0;
  if (status === 'embedding') return 85;
  if (status === 'ocr_processing') return 45;
  return 15;
}

function relativeTime(value: string): string {
  const parsed = new Date(value.includes('T') ? value : `${value.replace(' ', 'T')}Z`);
  if (Number.isNaN(parsed.getTime())) return '';
  const minutes = Math.floor((Date.now() - parsed.getTime()) / 60000);
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} ngày trước`;
  return parsed.toLocaleDateString('vi-VN');
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [totalAll, setTotalAll] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [subject, setSubject] = useState('Tất cả môn học');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [subjectTag, setSubjectTag] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (search.trim()) params.set('q', search.trim());
      if (subject !== 'Tất cả môn học') params.set('subject_tag', subject);
      const data = await apiRequest<DocumentListResponse>(`/api/documents?${params}`);
      setDocuments(data.items);
      setTotalAll(data.total_all);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được danh sách tài liệu.');
    } finally {
      setLoading(false);
    }
  }, [search, subject]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  // Tài liệu đang xử lý nền cần hỏi lại trạng thái cho tới khi sẵn sàng hoặc lỗi.
  useEffect(() => {
    const pending = documents.filter((doc) => PROCESSING_STATUSES.includes(doc.status));
    if (pending.length === 0) return;
    const timer = setTimeout(() => {
      void Promise.all(
        pending.map((doc) =>
          apiRequest<DocumentStatusResponse>(`/api/documents/${doc.id}/status`)
            .then((status) =>
              setDocuments((items) =>
                items.map((item) => (item.id === doc.id ? { ...item, ...status } : item)),
              ),
            )
            .catch(() => undefined),
        ),
      );
    }, 1500);
    return () => clearTimeout(timer);
  }, [documents]);

  const subjectOptions = useMemo(() => {
    const found = new Set<string>();
    documents.forEach((doc) => doc.subject_tag && found.add(doc.subject_tag));
    return ['Tất cả môn học', ...Array.from(found)];
  }, [documents]);

  const readyCount = documents.filter((doc) => doc.status === 'ready').length;
  const processingCount = documents.filter((doc) => PROCESSING_STATUSES.includes(doc.status)).length;

  const closeModal = () => {
    setUploadOpen(false);
    setFile(null);
    setSubjectTag('');
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const submitUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      if (subjectTag.trim()) form.append('subject_tag', subjectTag.trim());
      await apiUpload<DocumentItem>('/api/documents', form);
      closeModal();
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải lên được tài liệu.');
    } finally {
      setUploading(false);
    }
  };

  const removeDocument = async (documentId: number) => {
    setError('');
    try {
      await apiRequest<{ message: string }>(`/api/documents/${documentId}`, { method: 'DELETE' });
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không xoá được tài liệu.');
    }
  };

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow text-accent">Thư viện kiến thức</p>
          <h1 className="page-title mt-2 text-3xl text-ink">Tài liệu của bạn</h1>
          <p className="mt-2 text-sm text-muted">Tải lên, quản lý và khai thác tài liệu học tập.</p>
        </div>
        <button onClick={() => setUploadOpen(true)} className="btn btn-primary"><Plus size={17} />Tải tài liệu lên</button>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tổng tài liệu" value={String(totalAll)} detail="Tất cả định dạng" icon={FileText} tone="indigo" />
        <StatCard title="Đã sẵn sàng" value={String(readyCount)} detail="Có thể hỏi đáp ngay" icon={Check} tone="emerald" />
        <StatCard title="Đang xử lý" value={String(processingCount)} detail="OCR và tạo vector" icon={Clock3} tone="orange" />
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <X className="mt-0.5 shrink-0" size={17} />
          <span className="flex-1">{error}</span>
          <button aria-label="Đóng thông báo" onClick={() => setError('')}><X size={15} /></button>
        </div>
      )}

      <section className="card p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1"><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo tên tài liệu..." className="input input-icon" /></div>
          <div className="flex gap-2 overflow-x-auto">
            <label className="flex min-w-fit items-center gap-2 rounded-lg border border-line px-3 text-sm text-ink"><Filter size={15} className="text-muted" /><select aria-label="Lọc môn học" value={subject} onChange={(e) => setSubject(e.target.value)} className="h-11 bg-transparent pr-2 font-semibold outline-none">{subjectOptions.map((option) => <option key={option}>{option}</option>)}</select><ChevronDown size={14} /></label>
            <div className="flex rounded-lg bg-[#efece3] p-1"><button aria-label="Xem dạng lưới" onClick={() => setView('grid')} className={`rounded-md p-2 ${view === 'grid' ? 'bg-surface text-accent shadow-sm' : 'text-muted'}`}><Grid2X2 size={17} /></button><button aria-label="Xem dạng danh sách" onClick={() => setView('list')} className={`rounded-md p-2 ${view === 'list' ? 'bg-surface text-accent shadow-sm' : 'text-muted'}`}><List size={17} /></button></div>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="flex items-center justify-center gap-3 rounded-2xl border border-dashed border-line bg-surface py-16 text-muted">
          <Loader2 className="animate-spin" size={22} />
          <span className="text-sm font-semibold">Đang tải tài liệu…</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line bg-surface py-16 text-center"><FileText className="mx-auto text-[#c9c3b6]" size={40} /><p className="mt-3 font-semibold text-ink">Chưa có tài liệu nào</p><p className="mt-1 text-sm text-muted">Hãy tải lên tài liệu để bắt đầu hỏi đáp bằng trí tuệ nhân tạo.</p></div>
      ) : (
        <section className={view === 'grid' ? 'grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3' : 'space-y-3'}>
          {documents.map((doc) => (
            <article key={doc.id} className="card group p-5 transition hover:border-accent">
              <div className="flex items-start gap-4"><FileBadge type={TYPE_LABEL[doc.file_type]} /><div className="min-w-0 flex-1"><h2 className="truncate font-semibold text-ink group-hover:text-accent">{doc.file_name}</h2><p className="mt-1 truncate text-xs text-muted">{doc.subject_tag || doc.chapter_tag || 'Chưa phân loại'}</p></div><button aria-label="Xoá tài liệu" onClick={() => void removeDocument(doc.id)} className="rounded-lg p-2 text-muted transition hover:bg-rose-50 hover:text-rose-600"><Trash2 size={17} /></button></div>
              <div className="mt-5 flex items-center justify-between text-xs text-muted"><span>{formatFileSize(doc.file_size_kb)} • {doc.page_count ? `${doc.page_count} trang` : 'chưa rõ số trang'}</span><span className={`pill ${statusStyle(doc.status)}`}>{viewStyle(doc.status)}</span></div>
              <div className="mt-4 flex items-center gap-3"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#efece3]"><div className={`h-full rounded-full ${doc.status === 'error' ? 'bg-rose-400' : 'bg-accent'}`} style={{ width: `${progressOf(doc.status)}%` }} /></div><span className="text-[10px] font-bold text-muted">{progressOf(doc.status)}%</span></div>
              <p className="mt-3 truncate text-[11px] text-muted" title={doc.error_message ?? undefined}>{doc.status === 'error' && doc.error_message ? doc.error_message : `Cập nhật ${relativeTime(doc.created_at)}`}</p>
            </article>
          ))}
        </section>
      )}

      {uploadOpen && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-ink/45 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="upload-title" className="w-full max-w-lg rounded-2xl bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between"><div><h2 id="upload-title" className="section-title text-xl text-ink">Tải tài liệu mới</h2><p className="mt-1 text-sm text-muted">Tối đa 20 MB mỗi tệp</p></div><button aria-label="Đóng" onClick={closeModal} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink"><X size={19} /></button></div>

            <input ref={fileInputRef} type="file" accept={ACCEPTED} className="hidden" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(''); }} />
            <button onClick={() => fileInputRef.current?.click()} className="mt-6 w-full rounded-xl border-2 border-dashed border-line bg-[#faf9f5] px-6 py-10 text-center transition hover:border-accent hover:bg-accent-soft"><UploadCloud className="mx-auto text-accent" size={34} /><p className="mt-3 text-sm font-semibold text-accent">Nhấn để chọn tệp từ máy</p><p className="mt-1 text-xs text-muted">PDF, DOCX, XLSX, JPG hoặc PNG</p></button>

            {file && (
              <div className="mt-4 flex items-center gap-3 rounded-lg bg-paper p-3">
                <FileText className="shrink-0 text-rose-500" size={20} />
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{file.name}</p><p className="text-[11px] text-muted">{formatFileSize(Math.max(1, Math.round(file.size / 1024)))}</p></div>
                <Check size={17} className="shrink-0 text-emerald-600" />
              </div>
            )}

            <label className="field-label mt-4">Môn học (không bắt buộc)</label>
            <input value={subjectTag} onChange={(e) => setSubjectTag(e.target.value)} placeholder="Ví dụ: Trí tuệ nhân tạo" className="input" />

            {error && <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p>}

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={closeModal} disabled={uploading} className="btn btn-outline">Hủy</button>
              <button onClick={() => void submitUpload()} disabled={!file || uploading} className="btn btn-primary">
                {uploading ? <><Loader2 className="animate-spin" size={16} />Đang tải lên…</> : 'Tải lên'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

