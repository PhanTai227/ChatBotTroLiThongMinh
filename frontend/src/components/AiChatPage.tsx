import { useEffect, useRef, useState } from 'react';
import { apiRequest, apiStream, type Citation, type DocumentItem } from '../lib/auth';
import {
  Bot,
  BookOpen,
  ChevronDown,
  FileText,
  Lightbulb,
  Menu,
  MessageSquarePlus,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
  citations?: { title: string; page: string }[];
};

type ConversationItem = {
  id: number;
  title: string;
  created_at: string;
  message_count: number;
};

type LoadedMessage = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
};

const suggestions = [
  'Gradient Descent hoạt động như thế nào?',
  'So sánh thuật toán tìm kiếm tối ưu',
  'Giải thích khái niệm hàm mất mát',
];

/** Trích dẫn backend -> chip hiển thị: "Tên file · Trang N". */
function toChips(citations: Citation[]) {
  return citations.map((item, index) => ({
    title: item.file_name,
    page: item.page_number ? `Trang ${item.page_number}` : `Nguồn ${index + 1}`,
  }));
}

function formatTime(value: string) {
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
}

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
          {message.citations && message.citations.length > 0 && (
            <div className="mt-4 border-t border-line pt-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted">Nguồn tham khảo</p>
              <div className="flex flex-wrap gap-2">
                {message.citations.map((citation) => (
                  <span key={`${citation.title}-${citation.page}`} className="flex items-center gap-2 rounded-lg bg-accent-soft px-2.5 py-2 text-left text-[11px] font-semibold text-accent"><FileText size={13} /><span>{citation.title} · {citation.page}</span></span>
                ))}
              </div>
            </div>
          )}
          <p className="mt-2 text-right text-[10px] text-muted">{message.time}</p>
        </div>
      </div>
    </div>
  );
}


export function AiChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('all');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => {
    try {
      const data = await apiRequest<{ items: ConversationItem[] }>('/api/conversations');
      setConversations(data.items);
    } catch {
      /* sidebar trống khi chưa tải được */
    }
  };

  useEffect(() => {
    void loadConversations();
    apiRequest<{ items: DocumentItem[]; total_all: number }>('/api/documents?limit=100')
      .then((data) => setDocuments(data.items.filter((item) => item.status === 'ready')))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming, thinking]);

  const newChat = () => {
    setMessages([]);
    setActiveConversationId(null);
    setError('');
    setSidebarOpen(false);
  };

  const openConversation = async (id: number) => {
    setError('');
    setSidebarOpen(false);
    try {
      const data = await apiRequest<{ messages: LoadedMessage[] }>(`/api/conversations/${id}`);
      setActiveConversationId(id);
      setMessages(
        data.messages.map((item) => ({
          id: `m-${item.id}`,
          role: item.role,
          content: item.content,
          time: formatTime(item.created_at),
        })),
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Không mở được hội thoại.');
    }
  };

  const deleteConversation = async (id: number) => {
    if (!window.confirm('Xóa hội thoại này?')) return;
    try {
      await apiRequest(`/api/conversations/${id}`, { method: 'DELETE' });
      if (activeConversationId === id) {
        setMessages([]);
        setActiveConversationId(null);
      }
      await loadConversations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Xóa hội thoại thất bại.');
    }
  };

  const sendMessage = async (text: string) => {
    const question = text.trim();
    if (!question || streaming || thinking) return;
    setError('');
    setThinking(true);

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: question,
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    };
    const assistantId = `a-${Date.now()}`;
    setMessages((previous) => [...previous, userMessage]);
    setInput('');

    const documentId = selectedDocumentId === 'all' ? undefined : Number(selectedDocumentId);

    try {
      await apiStream(
        '/api/chat/stream',
        { message: question, conversation_id: activeConversationId, document_id: documentId },
        (event) => {
          if (event.type === 'meta') {
            setActiveConversationId(event.conversation_id);
            return;
          }
          if (event.type === 'delta') {
            setThinking(false);
            setStreaming(true);
            const piece = event.text;
            setMessages((previous) => {
              const exists = previous.some((item) => item.id === assistantId);
              if (!exists) {
   return [...previous, { id: assistantId, role: 'assistant', content: piece, time: '' }];
              }
              return previous.map((item) =>
                item.id === assistantId ? { ...item, content: item.content + piece } : item,
              );
            });
            return;
          }
          if (event.type === 'citations') {
            const chips = toChips(event.items);
            setMessages((previous) =>
              previous.map((item) =>
                item.id === assistantId ? { ...item, citations: chips } : item,
              ),
            );
            return;
          }
          if (event.type === 'error') {
            throw new Error(event.detail);
          }
        },
      );
      await loadConversations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Không gửi được câu hỏi.');
      setMessages((previous) => previous.filter((item) => item.id !== assistantId));
    } finally {
      setThinking(false);
      setStreaming(false);
    }
  };

  return (
    <div className="flex gap-4">
      <aside className={`w-[260px] shrink-0 space-y-2 ${sidebarOpen ? 'block' : 'hidden'} lg:block`}>
        <button onClick={newChat} className="btn btn-primary flex w-full items-center justify-center gap-2 px-4 py-3 text-sm">
          <Plus size={16} />Hội thoại mới
        </button>
        <div className="card max-h-[560px] space-y-1 overflow-y-auto p-3">
          {conversations.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-muted">Chưa có hội thoại nào.</p>
          )}
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`group flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition ${
                conversation.id === activeConversationId
                  ? 'bg-accent-soft font-semibold text-accent'
                  : 'text-muted hover:bg-[#efece3] hover:text-ink'
              }`}
            >
              <button onClick={() => void openConversation(conversation.id)} className="min-w-0 flex-1 text-left">
                <p className="truncate font-semibold">{conversation.title}</p>
                <p className="mt-0.5 text-[11px] opacity-70">{conversation.message_count} tin nhắn</p>
              </button>
              <button
                aria-label={`Xóa hội thoại ${conversation.title}`}
                onClick={() => void deleteConversation(conversation.id)}
                className="rounded-md p-1.5 text-muted opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="card flex min-h-[600px] min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-line p-3 sm:p-4">
          <button aria-label="Mở danh sách hội thoại" onClick={() => setSidebarOpen((open) => !open)} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink lg:hidden"><Menu size={18} /></button>
          <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-white"><Bot size={18} /></div>
          <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold text-ink">Trợ lý học tập AI</h1><p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted"><span className="size-1.5 rounded-full bg-emerald-500" />{streaming ? 'Đang trả lời...' : 'Sẵn sàng hỗ trợ'}</p></div>
          <label className="hidden max-w-[310px] flex-1 items-center gap-2 rounded-lg border border-line px-3 md:flex"><BookOpen size={15} className="shrink-0 text-muted" /><select aria-label="Chọn tài liệu" value={selectedDocumentId} onChange={(e) => setSelectedDocumentId(e.target.value)} className="h-10 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option value="all">Tất cả tài liệu</option>{documents.map((document) => <option key={document.id} value={String(document.id)}>{document.file_name}</option>)}</select><ChevronDown size={14} /></label>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-7">
          <div className="mx-auto max-w-4xl space-y-6">
            {messages.length === 0 && (
              <div className="mx-auto max-w-xl rounded-2xl bg-accent-soft p-5 text-center">
                <div className="mx-auto grid size-11 place-items-center rounded-lg bg-surface text-accent"><Lightbulb size={21} /></div>
                <h2 className="section-title mt-3 text-ink">AI local có thể giúp gì cho bạn?</h2>
                <p className="mt-1 text-xs leading-5 text-muted">Câu trả lời được tạo trên máy, không gửi nội dung lên dịch vụ trả phí.</p>
                <div className="mt-4 grid gap-2 sm:grid-cols-3">
                  {suggestions.map((suggestion) => <button key={suggestion} onClick={() => void sendMessage(suggestion)} className="rounded-lg border border-line bg-surface p-2.5 text-[11px] font-semibold leading-4 text-muted transition hover:border-accent hover:text-accent">{suggestion}</button>)}
                </div>
              </div>
            )}
            {messages.map((message) => <MessageItem key={message.id} message={message} />)}
            {thinking && <div className="flex gap-3"><div className="grid size-9 place-items-center rounded-lg bg-accent text-white"><Sparkles size={17} /></div><div className="rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-sm text-muted">AI local đang phân tích câu hỏi<span className="ml-1 inline-flex gap-1"><i className="size-1 animate-pulse rounded-full bg-accent" /><i className="size-1 animate-pulse rounded-full bg-accent [animation-delay:200ms]" /><i className="size-1 animate-pulse rounded-full bg-accent [animation-delay:400ms]" /></span></div></div>}
            {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div>}
            <div ref={bottomRef} />
          </div>
        </div>

        <footer className="border-t border-line bg-surface p-3 sm:p-4">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-2 md:hidden">
              <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-line px-3"><BookOpen size={15} className="shrink-0 text-muted" /><select aria-label="Chọn tài liệu" value={selectedDocumentId} onChange={(e) => setSelectedDocumentId(e.target.value)} className="h-10 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option value="all">Tất cả tài liệu</option>{documents.map((document) => <option key={document.id} value={String(document.id)}>{document.file_name}</option>)}</select><ChevronDown size={14} /></label>
              <button onClick={newChat} aria-label="Hội thoại mới" className="grid size-10 shrink-0 place-items-center rounded-lg border border-line text-muted hover:text-accent"><MessageSquarePlus size={17} /></button>
            </div>
            <div className="mt-2 flex items-end gap-2 rounded-xl border border-line bg-surface p-2 transition focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/15">
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage(input); } }} rows={1} placeholder="Nhập câu hỏi của bạn..." className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-5 text-ink outline-none placeholder:text-muted" />
              <button onClick={() => void sendMessage(input)} disabled={!input.trim() || thinking || streaming} aria-label="Gửi câu hỏi" className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent text-white transition hover:bg-accent-deep disabled:cursor-not-allowed disabled:bg-line"><Send size={17} /></button>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted">Trợ lý AI có thể mắc lỗi. Hãy kiểm tra trích dẫn tài liệu.</p>
          </div>
        </footer>
      </section>
    </div>
  );
}

