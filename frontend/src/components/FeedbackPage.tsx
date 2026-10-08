import { useEffect, useState } from 'react';
import { CheckCircle2, MessageSquareHeart, Send, Star } from 'lucide-react';
import { apiRequest } from '../lib/auth';

type FeedbackItem = {
  id: number;
  rating: number;
  category: 'bug' | 'suggestion' | 'praise' | 'other';
  content: string;
  status: 'new' | 'read' | 'replied';
  admin_reply: string | null;
  created_at: string;
};

const categoryLabels: Record<FeedbackItem['category'], string> = {
  bug: 'Lỗi hệ thống',
  suggestion: 'Góp ý cải thiện',
  praise: 'Đánh giá tốt',
  other: 'Khác',
};

const statusLabels: Record<FeedbackItem['status'], { label: string; className: string }> = {
  new: { label: 'Chờ xem', className: 'bg-amber-50 text-amber-700' },
  read: { label: 'Đã xem', className: 'bg-sky-50 text-sky-700' },
  replied: { label: 'Đã trả lời', className: 'bg-emerald-50 text-emerald-700' },
};

function formatDate(value: string) {
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('vi-VN');
}

export function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [rating, setRating] = useState(5);
  const [category, setCategory] = useState<FeedbackItem['category']>('other');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = async () => {
    try {
      const data = await apiRequest<{ items: FeedbackItem[] }>('/api/feedback');
      setItems(data.items);
      setError('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Không tải được phản hồi.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const submit = async () => {
    if (!content.trim() || sending) return;
    setSending(true);
    setError('');
    setSuccess('');
    try {
      await apiRequest('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({ rating, category, content: content.trim() }),
      });
      setContent('');
      setSuccess('Đã gửi phản hồi tới quản trị viên. Cảm ơn bạn!');
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Gửi phản hồi thất bại.');
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <section className="animate-fade-up">
        <p className="eyebrow text-accent">Kết nối với quản trị</p>
        <h1 className="page-title mt-2 text-3xl text-ink">Phản hồi & Đánh giá</h1>
        <p className="mt-2 text-sm text-muted">Gửi đánh giá về trải nghiệm học tập và xem trả lời từ quản trị viên.</p>
      </section>

      <section className="card p-5 sm:p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="grid size-9 place-items-center rounded-lg bg-accent-soft text-accent"><MessageSquareHeart size={17} /></div>
          <div><h2 className="section-title text-ink">Gửi phản hồi mới</h2><p className="mt-0.5 text-xs text-muted">Đánh giá của bạn giúp hệ thống tốt hơn mỗi ngày</p></div>
        </div>

        <div className="space-y-4">
          <div>
            <span className="field-label">Mức độ hài lòng</span>
            <div className="mt-1 flex gap-1">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-label={`Đánh giá ${value} sao`}
                  onClick={() => setRating(value)}
                  className={`rounded-lg p-1.5 transition ${value <= rating ? 'text-amber-500' : 'text-[#c9c3b6] hover:text-amber-400'}`}
                >
                  <Star size={26} fill={value <= rating ? 'currentColor' : 'none'} />
                </button>
              ))}
            </div>
          </div>

          <label className="block">
            <span className="field-label">Loại phản hồi</span>
            <select value={category} onChange={(e) => setCategory(e.target.value as FeedbackItem['category'])} className="input mt-1">
              <option value="other">Khác</option>
              <option value="bug">Lỗi hệ thống</option>
              <option value="suggestion">Góp ý cải thiện</option>
              <option value="praise">Đánh giá tốt</option>
            </select>
          </label>

          <label className="block">
            <span className="field-label">Nội dung</span>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              maxLength={2000}
              placeholder="Chia sẻ cảm nhận, lỗi bạn gặp hoặc ý tưởng cải thiện..."
              className="input mt-1 resize-none"
            />
          </label>

          {error && <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}
          {success && <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700"><CheckCircle2 size={16} />{success}</p>}

          <button
            onClick={() => void submit()}
            disabled={!content.trim() || sending}
            className="btn btn-primary px-5 py-3 text-sm disabled:cursor-not-allowed disabled:bg-line"
          >
            <Send size={16} />{sending ? 'Đang gửi...' : 'Gửi phản hồi'}
          </button>
        </div>
      </section>

      <section className="card p-5 sm:p-6">
        <h2 className="section-title text-ink">Phản hồi của tôi</h2>
        <p className="mt-1 text-xs text-muted">Theo dõi trạng thái và trả lời từ quản trị viên.</p>
        <div className="mt-4 space-y-3">
          {loading && <p className="py-6 text-center text-sm text-muted">Đang tải...</p>}
          {!loading && items.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line bg-paper py-10 text-center">
              <p className="font-semibold text-ink">Chưa có phản hồi nào</p>
              <p className="mt-1 text-sm text-muted">Hãy gửi đánh giá đầu tiên của bạn.</p>
            </div>
          )}
          {items.map((item) => {
            const itemStatus = statusLabels[item.status];
            return (
              <article key={item.id} className="rounded-xl border border-line bg-paper p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex gap-0.5 text-amber-500">
                    {[1, 2, 3, 4, 5].map((value) => (
                      <Star key={value} size={14} fill={value <= item.rating ? 'currentColor' : 'none'} />
                    ))}
                  </span>
                  <span className="pill bg-accent-soft text-accent">{categoryLabels[item.category]}</span>
                  <span className={`pill ${itemStatus.className}`}>{itemStatus.label}</span>
                  <span className="ml-auto text-[11px] text-muted">{formatDate(item.created_at)}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-ink">{item.content}</p>
                {item.admin_reply && (
                  <div className="mt-3 rounded-lg border-l-4 border-accent bg-accent-soft px-4 py-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-accent">Trả lời từ quản trị viên</p>
                    <p className="mt-1 text-sm leading-6 text-ink">{item.admin_reply}</p>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
