import { useState } from 'react';
import { apiRequest } from '../lib/auth';
import {
  Bot,
  BookOpen,
  ChevronDown,
  FileText,
  Lightbulb,
  Menu,
  MessageSquarePlus,
  Send,
  Sparkles,
  X,
} from 'lucide-react';

type ChatMessage = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  time: string;
  citations?: { title: string; page: string }[];
};

const conversations = [
  { id: 1, title: 'Học thuật toán tối ưu', time: '5 phút trước', active: true },
  { id: 2, title: 'So sánh RAG và fine-tuning', time: 'Hôm qua', active: false },
  { id: 3, title: 'Cách tính độ phức tạp', time: '2 ngày trước', active: false },
  { id: 4, title: 'Mạng nơ-ron có tích chập', time: '1 tuần trước', active: false },
];

const suggestions = [
  'Gradient Descent hoạt động như thế nào?',
  'So sánh thuật toán tìm kiếm tối ưu',
  'Giải thích khái niệm hàm mất mát',
];

const initialMessages: ChatMessage[] = [
  {
    id: 1,
    role: 'user',
    content: 'Gradient Descent hoạt động như thế nào?',
    time: '14:32',
  },
  {
    id: 2,
    role: 'assistant',
    content: 'Gradient Descent là thuật toán tối ưu hàm mất mát bằng cách di chuyển ngược hướng gradient.\n\nMỗi vòng lặp gồm 3 bước chính:',
    time: '14:32',
    citations: [
      { title: 'Giáo trình Trí tuệ nhân tạo', page: 'Trang 18' },
      { title: 'Slide Thuật toán tối ưu', page: 'Trang 7' },
    ],
  },
  {
    id: 3,
    role: 'assistant',
    content: '1. Tính gradient của hàm mất mát tại tham số hiện tại.\n2. Cập nhật tham số theo công thức θ = θ − α·∇J(θ), với α là tốc độ học.\n3. Lặp lại cho đến khi hàm mất mát giảm đủ nhỏ hoặc đạt số vòng lặp quy định.\n\nNếu learning rate quá lớn, mô hình có thể không hội tụ; nếu quá nhỏ, quá trình huấn luyện sẽ chậm.',
    time: '14:32',
  },
];

function MessageItem({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-3 text-sm leading-6 text-white sm:max-w-[70%]">
          <p>{message.content}</p><p className="mt-1 text-right text-[10px] text-white/60">{message.time}</p>
        </div>
        <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-[#efece3] text-xs font-bold text-muted">AN</div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-white"><Sparkles size={17} /></div>
      <div className="max-w-[90%] space-y-2 sm:max-w-[80%]">
        <div className="rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-sm leading-6 text-ink">
          <p className="whitespace-pre-line">{message.content}</p>
          {message.citations && (
            <div className="mt-4 border-t border-line pt-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted">Nguồn tham khảo</p>
              <div className="flex flex-wrap gap-2">
                {message.citations.map((citation) => (
                  <button key={citation.title} className="flex items-center gap-2 rounded-lg bg-accent-soft px-2.5 py-2 text-left text-[11px] font-semibold text-accent transition hover:bg-[#dde9e0]"><FileText size={13} /><span>{citation.title} · {citation.page}</span></button>
                ))}
              </div>
            </div>
          )}
          <p className="mt-3 border-t border-line pt-2 text-[10px] text-muted">{message.time}</p>
        </div>
      </div>
    </div>
  );
}

export function AiChatPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [selectedDocument, setSelectedDocument] = useState('Giáo trình Trí tuệ nhân tạo');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState('');

  const sendMessage = async (content: string) => {
    const question = content.trim();
    if (!question || isThinking) return;
    setError('');
    setMessages((items) => [...items, { id: Date.now(), role: 'user', content: question, time: 'Đang gửi' }]);
    setInput('');
    setIsThinking(true);

    try {
      const response = await apiRequest<{ answer: string; conversation_id: number; model: string }>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: question, conversation_id: conversationId }),
      });
      setConversationId(response.conversation_id);
      setMessages((items) => [
        ...items.map((item, index) => index === items.length - 1 ? { ...item, time: 'Vừa xong' } : item),
        { id: Date.now() + 1, role: 'assistant', content: response.answer, time: 'Vừa xong' },
      ]);
    } catch (requestError) {
      setMessages((items) => items.slice(0, -1));
      setError(requestError instanceof Error ? requestError.message : 'Có lỗi xảy ra. Hãy thử lại.');
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="-m-4 flex min-h-[calc(100vh-5rem)] overflow-hidden border-t border-line bg-paper sm:-m-7 lg:-m-9">
      <aside className={`${sidebarOpen ? 'fixed inset-0 z-50 flex w-[290px] shadow-2xl' : 'hidden'} w-[290px] shrink-0 flex-col border-r border-line bg-surface lg:static lg:flex lg:w-[280px] lg:shadow-none`}>
        <div className="border-b border-line p-4">
          <button className="btn btn-primary w-full"><MessageSquarePlus size={17} />Cuộc hội thoại mới</button>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto p-3">
          {conversations.map((conversation) => (
            <button key={conversation.id} onClick={() => setSidebarOpen(false)} className={`flex w-full items-start gap-3 rounded-lg p-3 text-left transition ${conversation.active ? 'bg-accent-soft' : 'hover:bg-[#f1eee6]'}`}><Bot size={16} className={conversation.active ? 'text-accent' : 'text-muted'} /><div className="min-w-0 flex-1"><p className={`truncate text-xs font-semibold ${conversation.active ? 'text-accent' : 'text-ink'}`}>{conversation.title}</p><p className="mt-1 text-[10px] text-muted">{conversation.time}</p></div></button>
          ))}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center gap-3 border-b border-line bg-surface px-4 sm:px-6">
          <button aria-label="Mở danh sách hội thoại" onClick={() => setSidebarOpen(true)} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink lg:hidden"><Menu size={19} /></button>
          <div className="grid size-9 place-items-center rounded-lg bg-accent text-white"><Bot size={18} /></div>
          <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold text-ink">Trợ lý học tập AI</h1><p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted"><span className="size-1.5 rounded-full bg-emerald-500" />Sẵn sàng hỗ trợ</p></div>
          <label className="hidden max-w-[310px] flex-1 items-center gap-2 rounded-lg border border-line px-3 md:flex"><BookOpen size={15} className="shrink-0 text-muted" /><select aria-label="Chọn tài liệu" value={selectedDocument} onChange={(e) => setSelectedDocument(e.target.value)} className="h-10 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option>Giáo trình Trí tuệ nhân tạo</option><option>Slide Thuật toán tối ưu</option><option>Bài tập Giải thuật tuần 3</option></select><ChevronDown size={14} /></label>
          <button aria-label="Đóng" onClick={() => setSidebarOpen(false)} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink lg:hidden"><X size={18} /></button>
        </header>



        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-7">
          <div className="mx-auto max-w-4xl space-y-6">
            <div className="mx-auto max-w-xl rounded-2xl bg-accent-soft p-5 text-center">
              <div className="mx-auto grid size-11 place-items-center rounded-lg bg-surface text-accent"><Lightbulb size={21} /></div>
              <h2 className="section-title mt-3 text-ink">AI local có thể giúp gì cho bạn?</h2>
              <p className="mt-1 text-xs leading-5 text-muted">Câu trả lời được tạo trên máy bằng Qwen 2.5 3B, không gửi nội dung lên dịch vụ trả phí.</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} className="rounded-lg border border-line bg-surface p-2.5 text-[11px] font-semibold leading-4 text-muted transition hover:border-accent hover:text-accent">{suggestion}</button>)}
              </div>
            </div>
            {messages.map((message) => <MessageItem key={message.id} message={message} />)}
            {isThinking && <div className="flex gap-3"><div className="grid size-9 place-items-center rounded-lg bg-accent text-white"><Sparkles size={17} /></div><div className="rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-sm text-muted">AI local đang phân tích câu hỏi<span className="ml-1 inline-flex gap-1"><i className="size-1 animate-pulse rounded-full bg-accent" /><i className="size-1 animate-pulse rounded-full bg-accent [animation-delay:200ms]" /><i className="size-1 animate-pulse rounded-full bg-accent [animation-delay:400ms]" /></span></div></div>}
            {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div>}
          </div>
        </div>

        <footer className="border-t border-line bg-surface p-3 sm:p-4">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-2 rounded-xl border border-line bg-surface p-2 transition focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/15">
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage(input); } }} rows={1} placeholder="Nhập câu hỏi của bạn..." className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-5 text-ink outline-none placeholder:text-muted" />
              <button onClick={() => void sendMessage(input)} disabled={!input.trim() || isThinking} aria-label="Gửi câu hỏi" className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent text-white transition hover:bg-accent-deep disabled:cursor-not-allowed disabled:bg-line"><Send size={17} /></button>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted">Trợ lý AI có thể mắc lỗi. Hãy kiểm tra trích dẫn tài liệu.</p>
          </div>
        </footer>
      </section>
    </div>
  );
}
