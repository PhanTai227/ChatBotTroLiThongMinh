import { useMemo, useState } from 'react';
import {
  Check,
  ChevronDown,
  Clock3,
  FileImage,
  FileText,
  FileType,
  Filter,
  Grid2X2,
  List,
  MoreHorizontal,
  Plus,
  Search,
  UploadCloud,
  X,
} from 'lucide-react';
import { StatCard } from './DashboardCards';

type DocumentStatus = 'Sẵn sàng' | 'Đang xử lý' | 'Lỗi';
type FileType = 'PDF' | 'DOCX' | 'XLSX' | 'Ảnh';

type LearningDocument = {
  id: number;
  title: string;
  subject: string;
  type: FileType;
  size: string;
  pages: number;
  status: DocumentStatus;
  updated: string;
  progress: number;
};

const initialDocuments: LearningDocument[] = [
  { id: 1, title: 'Giáo trình Trí tuệ nhân tạo', subject: 'Trí tuệ nhân tạo', type: 'PDF', size: '8.4 MB', pages: 42, status: 'Sẵn sàng', updated: '10 phút trước', progress: 100 },
  { id: 2, title: 'Slide Thuật toán tối ưu', subject: 'Thuật toán', type: 'PDF', size: '5.1 MB', pages: 28, status: 'Sẵn sàng', updated: 'Hôm qua', progress: 100 },
  { id: 3, title: 'Bài tập Giải thuật tuần 3', subject: 'Cấu trúc dữ liệu', type: 'DOCX', size: '1.8 MB', pages: 12, status: 'Đang xử lý', updated: '2 ngày trước', progress: 65 },
  { id: 4, title: 'Bảng tính Thuật toán', subject: 'Thuật toán', type: 'XLSX', size: '860 KB', pages: 6, status: 'Sẵn sàng', updated: '3 ngày trước', progress: 100 },
  { id: 5, title: 'Sơ đồ mạng neuron', subject: 'Trí tuệ nhân tạo', type: 'Ảnh', size: '2.3 MB', pages: 1, status: 'Lỗi', updated: '4 ngày trước', progress: 0 },
  { id: 6, title: 'Bài giảng Hệ số liên kết', subject: 'Toán rời rạc', type: 'PDF', size: '4.7 MB', pages: 31, status: 'Sẵn sàng', updated: '1 tuần trước', progress: 100 },
];

const typeStyle: Record<FileType, string> = {
  PDF: 'bg-rose-50 text-rose-600',
  DOCX: 'bg-sky-50 text-sky-600',
  XLSX: 'bg-emerald-50 text-emerald-600',
  'Ảnh': 'bg-violet-50 text-violet-600',
};

function FileBadge({ type }: { type: FileType }) {
  return <div className={`grid size-12 shrink-0 place-items-center rounded-2xl text-[10px] font-extrabold ${typeStyle[type]}`}>{type === 'Ảnh' ? <FileImage size={21} /> : type}</div>;
}

function statusStyle(status: DocumentStatus) {
  if (status === 'Sẵn sàng') return 'bg-emerald-50 text-emerald-700';
  if (status === 'Lỗi') return 'bg-rose-50 text-rose-700';
  return 'bg-amber-50 text-amber-700';
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState(initialDocuments);
  const [search, setSearch] = useState('');
  const [subject, setSubject] = useState('Tất cả môn học');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState('');

  const filtered = useMemo(() => documents.filter((doc) => {
    const matchesSearch = doc.title.toLowerCase().includes(search.toLowerCase());
    return matchesSearch && (subject === 'Tất cả môn học' || doc.subject === subject);
  }), [documents, search, subject]);

  const addDemoDocument = () => {
    const name = uploadName.trim() || 'Tài liệu mới';
    setDocuments((items) => [{ id: Date.now(), title: name, subject: 'Chưa phân loại', type: 'PDF', size: '2.1 MB', pages: 1, status: 'Đang xử lý', updated: 'Vừa xong', progress: 20 }, ...items]);
    setUploadOpen(false);
    setUploadName('');
  };

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-indigo-500">Thư viện kiến thức</p><h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl">Tài liệu của bạn</h1><p className="mt-2 text-sm text-slate-500">Tải lên, quản lý và khai thác tài liệu học tập.</p></div>
        <button onClick={() => setUploadOpen(true)} className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:bg-indigo-700"><Plus size={18} />Tải tài liệu lên</button>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tổng tài liệu" value={String(documents.length)} detail="Tất cả định dạng" icon={FileText} tone="indigo" />
        <StatCard title="Đã sẵn sàng" value={String(documents.filter((d) => d.status === 'Sẵn sàng').length)} detail="Có thể hỏi đáp ngay" icon={Check} tone="emerald" />
        <StatCard title="Đang xử lý" value={String(documents.filter((d) => d.status === 'Đang xử lý').length)} detail="OCR và tạo vector" icon={Clock3} tone="orange" />
      </section>

      <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1"><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo tên tài liệu..." className="w-full rounded-xl border border-slate-200 py-3 pl-11 pr-4 text-sm outline-none focus:border-indigo-300 focus:ring-4 focus:ring-indigo-100" /></div>
          <div className="flex gap-2 overflow-x-auto">
            <label className="flex min-w-fit items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm text-slate-600"><Filter size={16} /><select aria-label="Lọc môn học" value={subject} onChange={(e) => setSubject(e.target.value)} className="h-12 bg-transparent pr-2 font-semibold outline-none"><option>Tất cả môn học</option><option>Trí tuệ nhân tạo</option><option>Thuật toán</option><option>Cấu trúc dữ liệu</option><option>Toán rời rạc</option><option>Chưa phân loại</option></select><ChevronDown size={14} /></label>
            <div className="flex rounded-xl bg-slate-100 p-1"><button aria-label="Xem dạng lưới" onClick={() => setView('grid')} className={`rounded-lg p-2.5 ${view === 'grid' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}><Grid2X2 size={18} /></button><button aria-label="Xem dạng danh sách" onClick={() => setView('list')} className={`rounded-lg p-2.5 ${view === 'list' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}><List size={18} /></button></div>
          </div>
        </div>
      </section>

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center"><FileText className="mx-auto text-slate-300" size={42} /><p className="mt-3 font-bold text-slate-700">Không tìm thấy tài liệu</p><p className="mt-1 text-sm text-slate-400">Hãy thử từ khóa hoặc bộ lọc khác.</p></div>
      ) : (
        <section className={view === 'grid' ? 'grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3' : 'space-y-3'}>
          {filtered.map((doc) => (
            <article key={doc.id} className="group rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] transition hover:-translate-y-0.5 hover:border-indigo-100 hover:shadow-lg">
              <div className="flex items-start gap-4"><FileBadge type={doc.type} /><div className="min-w-0 flex-1"><h2 className="truncate font-extrabold text-slate-800 group-hover:text-indigo-600">{doc.title}</h2><p className="mt-1 text-xs text-slate-400">{doc.subject}</p></div><button aria-label="Tùy chọn" className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600"><MoreHorizontal size={19} /></button></div>
              <div className="mt-5 flex items-center justify-between text-xs text-slate-400"><span>{doc.size} • {doc.pages} trang</span><span className={`rounded-full px-2.5 py-1 font-bold ${statusStyle(doc.status)}`}>{doc.status}</span></div>
              <div className="mt-4 flex items-center gap-3"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${doc.status === 'Lỗi' ? 'bg-rose-400' : 'bg-indigo-500'}`} style={{ width: `${doc.progress}%` }} /></div><span className="text-[10px] font-bold text-slate-400">{doc.progress}%</span></div>
              <p className="mt-3 text-[11px] text-slate-400">Cập nhật {doc.updated}</p>
            </article>
          ))}
        </section>
      )}

      {uploadOpen && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) setUploadOpen(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="upload-title" className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between"><div><h2 id="upload-title" className="text-xl font-extrabold text-slate-900">Tải tài liệu mới</h2><p className="mt-1 text-sm text-slate-400">Tối đa 20 MB mỗi tệp</p></div><button aria-label="Đóng" onClick={() => setUploadOpen(false)} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100"><X size={20} /></button></div>
            <button onClick={() => setUploadName('Giáo trình mới.pdf')} className="mt-6 w-full rounded-2xl border-2 border-dashed border-indigo-200 bg-indigo-50/60 px-6 py-10 text-center transition hover:border-indigo-400 hover:bg-indigo-50"><UploadCloud className="mx-auto text-indigo-500" size={38} /><p className="mt-3 text-sm font-extrabold text-indigo-700">Nhấn để chọn tệp từ máy</p><p className="mt-1 text-xs text-slate-400">PDF, DOCX, XLSX, JPG hoặc PNG</p></button>
            {uploadName && <div className="mt-4 flex items-center gap-3 rounded-xl bg-slate-50 p-3"><FileType className="text-rose-500" size={22} /><div className="flex-1"><p className="truncate text-sm font-bold text-slate-700">{uploadName}</p><p className="text-[11px] text-slate-400">Sẵn sàng tải lên</p></div><Check size={18} className="text-emerald-500" /></div>}
            <div className="mt-6 flex justify-end gap-3"><button onClick={() => setUploadOpen(false)} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600">Hủy</button><button onClick={addDemoDocument} className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white">Tải lên</button></div>
          </div>
        </div>
      )}
    </>
  );
}

