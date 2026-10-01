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
  PDF: 'bg-rose-50 text-rose-600',
  DOCX: 'bg-sky-50 text-sky-600',
  XLSX: 'bg-emerald-50 text-emerald-600',
  'Ảnh': 'bg-violet-50 text-violet-600',
};

function FileBadge({ type }: { type: FileType }) {
  return <div className={`grid size-12 shrink-0 place-items-center rounded-2xl text-[10px] font-extrabold ${typeStyle[type]}`}>{type === 'Ảnh' ? <FileImage size={21} /> : type}</div>;
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
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-indigo-500">Thư viện kiến thức</p><h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl">Tài liệu của bạn</h1><p className="mt-2 text-sm text-slate-500">Tải lên, quản lý và khai thác tài liệu học tập.</p></div>
        <button onClick={() => setUploadOpen(true)} className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:bg-indigo-700"><Plus size={18} />Tải tài liệu lên</button>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tổng tài liệu" value={String(totalAll)} detail="Tất cả định dạng" icon={FileText} tone="indigo" />
        <StatCard title="Đã sẵn sàng" value={String(readyCount)} detail="Có thể hỏi đáp ngay" icon={Check} tone="emerald" />
        <StatCard title="Đang xử lý" value={String(processingCount)} detail="OCR và tạo vector" icon={Clock3} tone="orange" />
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <X className="mt-0.5 shrink-0" size={18} />
          <span className="flex-1">{error}</span>
          <button aria-label="Đóng thông báo" onClick={() => setError('')}><X size={16} /></button>
        </div>
      )}

      <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1"><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo tên tài liệu..." className="w-full rounded-xl border border-slate-200 py-3 pl-11 pr-4 text-sm outline-none focus:border-indigo-300 focus:ring-4 focus:ring-indigo-100" /></div>
          <div className="flex gap-2 overflow-x-auto">
            <label className="flex min-w-fit items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm text-slate-600"><Filter size={16} /><select aria-label="Lọc môn học" value={subject} onChange={(e) => setSubject(e.target.value)} className="h-12 bg-transparent pr-2 font-semibold outline-none">{subjectOptions.map((option) => <option key={option}>{option}</option>)}</select><ChevronDown size={14} /></label>
            <div className="flex rounded-xl bg-slate-100 p-1"><button aria-label="Xem dạng lưới" onClick={() => setView('grid')} className={`rounded-lg p-2.5 ${view === 'grid' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}><Grid2X2 size={18} /></button><button aria-label="Xem dạng danh sách" onClick={() => setView('list')} className={`rounded-lg p-2.5 ${view === 'list' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}><List size={18} /></button></div>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="flex items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-slate-400">
          <Loader2 className="animate-spin" size={24} />
          <span className="text-sm font-semibold">Đang tải tài liệu…</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center"><FileText className="mx-auto text-slate-300" size={42} /><p className="mt-3 font-bold text-slate-700">Chưa có tài liệu nào</p><p className="mt-1 text-sm text-slate-400">Hãy tải lên tài liệu để bắt đầu hỏi đáp bằng trí tuệ nhân tạo.</p></div>
      ) : (
        <section className={view === 'grid' ? 'grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3' : 'space-y-3'}>
          {documents.map((doc) => (
            <article key={doc.id} className="group rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] transition hover:-translate-y-0.5 hover:border-indigo-100 hover:shadow-lg">
              <div className="flex items-start gap-4"><FileBadge type={TYPE_LABEL[doc.file_type]} /><div className="min-w-0 flex-1"><h2 className="truncate font-extrabold text-slate-800 group-hover:text-indigo-600">{doc.file_name}</h2><p className="mt-1 truncate text-xs text-slate-400">{doc.subject_tag || doc.chapter_tag || 'Chưa phân loại'}</p></div><button aria-label="Xoá tài liệu" onClick={() => void removeDocument(doc.id)} className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><Trash2 size={18} /></button></div>
              <div className="mt-5 flex items-center justify-between text-xs text-slate-400"><span>{formatFileSize(doc.file_size_kb)} • {doc.page_count ? `${doc.page_count} trang` : 'chưa rõ số trang'}</span><span className={`rounded-full px-2.5 py-1 font-bold ${statusStyle(doc.status)}`}>{viewStyle(doc.status)}</span></div>
              <div className="mt-4 flex items-center gap-3"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${doc.status === 'error' ? 'bg-rose-400' : 'bg-indigo-500'}`} style={{ width: `${progressOf(doc.status)}%` }} /></div><span className="text-[10px] font-bold text-slate-400">{progressOf(doc.status)}%</span></div>
              <p className="mt-3 truncate text-[11px] text-slate-400" title={doc.error_message ?? undefined}>{doc.status === 'error' && doc.error_message ? doc.error_message : `Cập nhật ${relativeTime(doc.created_at)}`}</p>
            </article>
          ))}
        </section>
      )}

      {uploadOpen && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="upload-title" className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between"><div><h2 id="upload-title" className="text-xl font-extrabold text-slate-900">Tải tài liệu mới</h2><p className="mt-1 text-sm text-slate-400">Tối đa 20 MB mỗi tệp</p></div><button aria-label="Đóng" onClick={closeModal} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100"><X size={20} /></button></div>

            <input ref={fileInputRef} type="file" accept={ACCEPTED} className="hidden" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(''); }} />
            <button onClick={() => fileInputRef.current?.click()} className="mt-6 w-full rounded-2xl border-2 border-dashed border-indigo-200 bg-indigo-50/60 px-6 py-10 text-center transition hover:border-indigo-400 hover:bg-indigo-50"><UploadCloud className="mx-auto text-indigo-500" size={38} /><p className="mt-3 text-sm font-extrabold text-indigo-700">Nhấn để chọn tệp từ máy</p><p className="mt-1 text-xs text-slate-400">PDF, DOCX, XLSX, JPG hoặc PNG</p></button>

            {file && (
              <div className="mt-4 flex items-center gap-3 rounded-xl bg-slate-50 p-3">
                <FileText className="shrink-0 text-rose-500" size={22} />
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold text-slate-700">{file.name}</p><p className="text-[11px] text-slate-400">{formatFileSize(Math.max(1, Math.round(file.size / 1024)))}</p></div>
                <Check size={18} className="shrink-0 text-emerald-500" />
              </div>
            )}

            <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-slate-500">Môn học (không bắt buộc)</label>
            <input value={subjectTag} onChange={(e) => setSubjectTag(e.target.value)} placeholder="Ví dụ: Trí tuệ nhân tạo" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-indigo-300 focus:ring-4 focus:ring-indigo-100" />

            {error && <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p>}

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={closeModal} disabled={uploading} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 disabled:opacity-50">Hủy</button>
              <button onClick={() => void submitUpload()} disabled={!file || uploading} className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
                {uploading ? <><Loader2 className="animate-spin" size={16} />Đang tải lên…</> : 'Tải lên'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

