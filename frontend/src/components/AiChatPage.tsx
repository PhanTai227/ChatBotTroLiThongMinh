import { useState } from 'react';
import { apiRequest } from '../lib/auth';
import {
  Bot,
  BookOpen,
  Check,
  ChevronDown,
  Copy,
  FileText,
  Lightbulb,
  MessageSquarePlus,
  MoreHorizontal,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
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
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-3 text-sm leading-6 text-white shadow-md shadow-indigo-100 sm:max-w-[70%]">
          <p>{message.content}</p><p className="mt-1 text-right text-[10px] text-indigo-200">{message.time}</p>
        </div>
        <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-slate-200 text-xs font-extrabold text-slate-600">AN</div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-200"><Sparkles size={18} /></div>
      <div className="max-w-[90%] space-y-3 sm:max-w-[80%]">
        <div className="rounded-2xl rounded-tl-md border border-slate-100 bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm">
          <p className="whitespace-pre-line">{message.content}</p>
          {message.citations && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <p className="mb-2 text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Nguồn tham khảo</p>
              <div className="flex flex-wrap gap-2">
                {message.citations.map((citation) => (
                  <button key={citation.title} className="flex items-center gap-2 rounded-lg bg-indigo-50 px-2.5 py-2 text-left text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100"><FileText size={13} /><span>{citation.title} · {citation.page}</span></button>
                ))}
              </div>
            </div>
          )}
          <div className="mt-3 flex items-center gap-1 border-t border-slate-100 pt-2 text-[10px] text-slate-400">
            <span>{message.time}</span><button aria-label="Sao chép" className="ml-2 rounded p-1 hover:bg-slate-100 hover:text-slate-600"><Copy size={13} /></button><button aria-label="Câu trả lời hữu ích" className="rounded p-1 hover:bg-emerald-50 hover:text-emerald-600"><ThumbsUp size={13} /></button><button aria-label="Câu trả lời chưa hữu ích" className="rounded p-1 hover:bg-rose-50 hover:text-rose-600"><ThumbsDown size={13} /></button>
          </div>
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
    <div className="-m-4 flex min-h-[calc(100vh-5rem)] overflow-hidden border-t border-slate-100 bg-[#f6f7fb] sm:-m-7 lg:-m-9">
      <aside className={`${sidebarOpen ? 'fixed inset-0 z-50 flex w-[290px] shadow-2xl' : 'hidden'} w-[290px] shrink-0 flex-col border-r border-slate-200 bg-white lg:static lg:flex lg:w-[280px] lg:shadow-none`}>
        <div className="border-b border-slate-100 p-4">
          <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-extrabold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700"><MessageSquarePlus size={18} />Cuộc hội thoại mới</button>
          <div className="mt-3 flex gap-2"><button className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-500">Hôm nay</button><button className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-500">7 ngày trước</button></div>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto p-3">
          {conversations.map((conversation) => (
            <button key={conversation.id} onClick={() => setSidebarOpen(false)} className={`flex w-full items-start gap-3 rounded-xl p-3 text-left transition ${conversation.active ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}><Bot size={17} className={conversation.active ? 'text-indigo-600' : 'text-slate-400'} /><div className="min-w-0 flex-1"><p className={`truncate text-xs font-bold ${conversation.active ? 'text-indigo-800' : 'text-slate-600'}`}>{conversation.title}</p><p className="mt-1 text-[10px] text-slate-400">{conversation.time}</p></div>{conversation.active && <MoreHorizontal size={15} className="text-indigo-400" />}</button>
          ))}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-20 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <button aria-label="Mở danh sách hội thoại" onClick={() => setSidebarOpen(true)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"><Plus size={20} /></button>
          <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white"><Bot size={20} /></div>
          <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-extrabold text-slate-900">Trợ lý học tập AI</h1><p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-slate-400"><span className="size-1.5 rounded-full bg-emerald-500" />Sẵn sàng hỗ trợ</p></div>
          <label className="hidden max-w-[310px] flex-1 items-center gap-2 rounded-xl border border-slate-200 px-3 md:flex"><BookOpen size={16} className="shrink-0 text-slate-400" /><select aria-label="Chọn tài liệu" value={selectedDocument} onChange={(e) => setSelectedDocument(e.target.value)} className="h-11 min-w-0 flex-1 bg-transparent text-xs font-semibold text-slate-600 outline-none"><option>Giáo trình Trí tuệ nhân tạo</option><option>Slide Thuật toán tối ưu</option><option>Bài tập Giải thuật tuần 3</option></select><ChevronDown size={14} /></label>
          <button aria-label="Đóng" onClick={() => setSidebarOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 lg:hidden"><X size={19} /></button>
        </header>



        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-7">
          <div className="mx-auto max-w-4xl space-y-6">
            <div className="mx-auto max-w-xl rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 to-indigo-50 p-5 text-center">
              <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-violet-600 shadow-md"><Lightbulb size={23} /></div>
              <h2 className="mt-3 font-extrabold text-slate-800">AI local có thể giúp gì cho bạn?</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">Câu trả lời được tạo trên máy bằng Qwen 2.5 3B, không gửi nội dung lên dịch vụ trả phí. RAG tài liệu sẽ kết nối ở bước tiếp theo.</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} className="rounded-xl border border-white bg-white/80 p-2.5 text-[11px] font-semibold leading-4 text-slate-600 shadow-sm hover:border-indigo-200 hover:text-indigo-700">{suggestion}</button>)}
              </div>
            </div>
            {messages.map((message) => <MessageItem key={message.id} message={message} />)}
            {isThinking && <div className="flex gap-3"><div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white"><Sparkles size={18} /></div><div className="rounded-2xl rounded-tl-md border border-slate-100 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">AI local đang phân tích câu hỏi<span className="ml-1 inline-flex gap-1"><i className="size-1 animate-pulse rounded-full bg-indigo-500" /><i className="size-1 animate-pulse rounded-full bg-indigo-500 [animation-delay:200ms]" /><i className="size-1 animate-pulse rounded-full bg-indigo-500 [animation-delay:400ms]" /></span></div></div>}
            {error && <div className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div>}
          </div>
        </div>

        <footer className="border-t border-slate-200 bg-white p-3 sm:p-4">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg shadow-slate-200/40 focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-100">
              <button aria-label="Đính kèm" className="grid size-10 shrink-0 place-items-center rounded-xl text-slate-400 hover:bg-slate-100 hover:text-indigo-600"><Paperclip size={19} /></button>
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage(input); } }} rows={1} placeholder="Nhập câu hỏi của bạn..." className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-1 py-2 text-sm leading-5 text-slate-700 outline-none placeholder:text-slate-400" />
              <button onClick={() => void sendMessage(input)} disabled={!input.trim() || isThinking} aria-label="Gửi câu hỏi" className="grid size-10 shrink-0 place-items-center rounded-xl bg-indigo-600 text-white shadow-md transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-200"><Send size={18} /></button>
            </div>
            <p className="mt-2 text-center text-[10px] text-slate-400">Trợ lý AI có thể mắc lỗi. Hãy kiểm tra trích dẫn tài liệu.</p>
          </div>
        </footer>
      </section>
    </div>
  );
}
