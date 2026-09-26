import { useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Check,
  CheckCircle2,
  Clock3,
  FileQuestion,
  ListChecks,
  RotateCcw,
  Sparkles,
  Target,
  Trophy,
  XCircle,
} from 'lucide-react';
import { StatCard } from './DashboardCards';

type QuizStatus = 'ready' | 'processing' | 'completed';

type QuizSummary = {
  id: number;
  title: string;
  document: string;
  questions: number;
  duration: number;
  status: QuizStatus;
  bestScore?: number;
  color: string;
};

type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
};

const quizzes: QuizSummary[] = [
  { id: 1, title: 'Kiểm tra Chương 2: Thuật toán tối ưu', document: 'Giáo trình Trí tuệ nhân tạo', questions: 10, duration: 10, status: 'ready', color: 'bg-indigo-50 text-indigo-600' },
  { id: 2, title: 'Ôn tập Gradient Descent', document: 'Slide Thuật toán tối ưu', questions: 8, duration: 8, status: 'completed', bestScore: 85, color: 'bg-rose-50 text-rose-600' },
  { id: 3, title: 'Câu hỏi về hàm mất mát', document: 'Bài giảng Hồi quy', questions: 12, duration: 15, status: 'ready', color: 'bg-emerald-50 text-emerald-600' },
  { id: 4, title: 'Quiz mạng nơ-ron', document: 'Giáo trình Trí tuệ nhân tạo', questions: 15, duration: 20, status: 'processing', color: 'bg-violet-50 text-violet-600' },
  { id: 5, title: 'Đề thi cuối chương 1', document: 'Slide Trí tuệ nhân tạo', questions: 20, duration: 25, status: 'completed', bestScore: 92, color: 'bg-amber-50 text-amber-600' },
];

const questions: QuizQuestion[] = [
  { id: 1, question: 'Gradient Descent cập nhật tham số mô hình theo hướng nào?', options: ['Cùng hướng với gradient', 'Ngược hướng với gradient', 'Ngẫu nhiên', 'Không thay đổi tham số'], correct: 1, explanation: 'Gradient Descent di chuyển ngược hướng gradient để hàm mất mát giảm dần.' },
  { id: 2, question: 'Ý nghĩa của learning rate trong quá trình huấn luyện là gì?', options: ['Số lượng dữ liệu huấn luyện', 'Tốc độ cập nhật tham số mô hình', 'Số lớp của mạng', 'Tên của thuật toán'], correct: 1, explanation: 'Learning rate α kiểm soát độ lớn của bước cập nhật tham số: θ = θ − α·∇J(θ).' },
  { id: 3, question: 'Nếu learning rate quá lớn, quá trình huấn luyện có khả năng xảy ra hiện tượng gì?', options: ['Hội tụ rất nhanh', 'Không thay đổi hàm mất mát', 'Dao động hoặc không hội tụ', 'Luôn cho giá trị tối ưu tuyệt đối'], correct: 2, explanation: 'Bước cập nhật quá lớn có thể vượt qua vùng tối ưu, làm giá trị hàm mất mát dao động hoặc phân kỳ.' },
];

function statusText(status: QuizStatus) {
  if (status === 'completed') return 'Đã hoàn thành';
  if (status === 'processing') return 'Đang tạo';
  return 'Sẵn sàng';
}

export function QuizPage() {
  const [screen, setScreen] = useState<'list' | 'quiz' | 'result'>('list');
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [filter, setFilter] = useState('Tất cả');

  const score = questions.reduce((total, question) => total + (answers[question.id] === question.correct ? 1 : 0), 0);
  const percent = Math.round((score / questions.length) * 100);
  const question = questions[current];

  const startQuiz = () => {
    setAnswers({});
    setCurrent(0);
    setScreen('quiz');
  };

  const nextQuestion = () => {
    if (current === questions.length - 1) setScreen('result');
    else setCurrent((value) => value + 1);
  };

  if (screen === 'quiz') {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <button onClick={() => setScreen('list')} className="flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-indigo-600"><ArrowLeft size={18} />Thoát bài làm</button>
          <div className="flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-xs font-bold text-slate-500 shadow-sm"><Clock3 size={16} />08:32</div>
        </div>
        <div className="mb-5"><div className="mb-2 flex justify-between text-xs font-semibold text-slate-500"><span>Câu {current + 1}/{questions.length}</span><span>{Math.round(((current + 1) / questions.length) * 100)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${((current + 1) / questions.length) * 100}%` }} /></div></div>
        <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-[0_8px_30px_rgba(15,23,42,0.05)] sm:p-8">
          <div className="mb-5 flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-indigo-600"><FileQuestion size={18} />Câu hỏi trắc nghiệm</div>
          <h1 className="text-xl font-extrabold leading-8 text-slate-900 sm:text-2xl">{question.question}</h1>
          <div className="mt-6 space-y-3">
            {question.options.map((option, index) => {
              const selected = answers[question.id] === index;
              return <button key={option} onClick={() => setAnswers((items) => ({ ...items, [question.id]: index }))} className={`flex w-full items-center gap-4 rounded-2xl border p-4 text-left text-sm font-semibold transition ${selected ? 'border-indigo-500 bg-indigo-50 text-indigo-800 ring-2 ring-indigo-100' : 'border-slate-200 text-slate-600 hover:border-indigo-300 hover:bg-slate-50'}`}><span className={`grid size-8 shrink-0 place-items-center rounded-lg text-xs font-extrabold ${selected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'}`}>{String.fromCharCode(65 + index)}</span><span className="flex-1">{option}</span>{selected && <Check size={19} className="text-indigo-600" />}</button>;
            })}
          </div>
          <div className="mt-8 flex justify-end"><button disabled={answers[question.id] === undefined} onClick={nextQuestion} className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 disabled:cursor-not-allowed disabled:bg-slate-300">{current === questions.length - 1 ? 'Xem kết quả' : 'Câu tiếp theo'}<ArrowRight size={17} /></button></div>
        </section>
      </div>
    );
  }


function statusClass(status: QuizStatus) {
  if (status === 'completed') return 'bg-emerald-50 text-emerald-700';
  if (status === 'processing') return 'bg-amber-50 text-amber-700';
  return 'bg-indigo-50 text-indigo-700';
}


  if (screen === 'result') {
    return (
      <div className="mx-auto max-w-3xl text-center">
        <section className="rounded-3xl border border-slate-100 bg-white p-7 shadow-[0_8px_30px_rgba(15,23,42,0.05)] sm:p-10">
          <div className={`mx-auto grid size-20 place-items-center rounded-3xl ${percent >= 70 ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>{percent >= 70 ? <Trophy size={38} /> : <Target size={38} />}</div>
          <p className="mt-5 text-xs font-extrabold uppercase tracking-[0.15em] text-indigo-500">Kết quả bài làm</p>
          <h1 className="mt-2 text-3xl font-extrabold text-slate-950">Hoàn thành xong!</h1>
          <p className="mt-2 text-sm text-slate-500">Bạn đã trả lời đúng {score}/{questions.length} câu hỏi.</p>
          <div className="mx-auto mt-7 grid size-32 place-items-center rounded-full border-8 border-indigo-100 bg-indigo-50 text-4xl font-extrabold text-indigo-700">{percent}%</div>
          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-emerald-50 p-4"><CheckCircle2 className="mx-auto text-emerald-600" size={22} /><p className="mt-2 text-xl font-extrabold text-emerald-700">{score}</p><p className="text-xs text-emerald-600">Đúng</p></div>
            <div className="rounded-2xl bg-rose-50 p-4"><XCircle className="mx-auto text-rose-600" size={22} /><p className="mt-2 text-xl font-extrabold text-rose-700">{questions.length - score}</p><p className="text-xs text-rose-600">Sai</p></div>
            <div className="rounded-2xl bg-indigo-50 p-4"><Clock3 className="mx-auto text-indigo-600" size={22} /><p className="mt-2 text-xl font-extrabold text-indigo-700">03:24</p><p className="text-xs text-indigo-600">Thời gian</p></div>
          </div>
          <section className="mt-7 rounded-2xl border border-slate-100 bg-slate-50 p-5 text-left">
            <h2 className="flex items-center gap-2 text-sm font-extrabold text-slate-800"><BookOpen size={18} className="text-indigo-600" />Giải thích câu cuối</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">{questions[questions.length - 1].explanation}</p>
          </section>
          <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row"><button onClick={() => setScreen('list')} className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">Về danh sách</button><button onClick={startQuiz} className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white"><RotateCcw size={17} />Làm lại</button></div>
        </section>
      </div>
    );
  }


  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-indigo-500">Luyện tập và tự kiểm tra</p><h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl">Bài tập & Quiz</h1><p className="mt-2 text-sm text-slate-500">Ôn tập kiến thức và theo dõi kết quả của bạn.</p></div>
        <button onClick={startQuiz} className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200"><Sparkles size={18} />Tạo quiz từ tài liệu</button>
      </section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Quiz đã hoàn thành" value="12" detail="Trong tháng này" icon={ListChecks} tone="indigo" />
        <StatCard title="Điểm trung bình" value="86%" detail="↗ 4% so với tháng trước" icon={Award} tone="emerald" />
        <StatCard title="Chuỗi học tập" value="7 ngày" detail="Tiếp tục để giữ chuỗi" icon={Trophy} tone="orange" />
      </section>
      <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
        <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="font-extrabold text-slate-900">Danh sách bài kiểm tra</h2><p className="mt-1 text-xs text-slate-400">Chọn một bài để bắt đầu làm</p></div><select aria-label="Lọc trạng thái quiz" value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600"><option>Tất cả</option><option>Sẵn sàng</option><option>Đã hoàn thành</option><option>Đang tạo</option></select></div>
        <div className="space-y-3">
          {quizzes.filter((quiz) => filter === 'Tất cả' || statusText(quiz.status) === filter).map((quiz) => (
            <article key={quiz.id} className="flex flex-col gap-4 rounded-2xl border border-slate-100 p-4 transition hover:border-indigo-200 hover:bg-indigo-50/20 sm:flex-row sm:items-center">
              <div className={`grid size-12 shrink-0 place-items-center rounded-2xl ${quiz.color}`}><FileQuestion size={23} /></div>
              <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-extrabold text-slate-800">{quiz.title}</h3><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${statusClass(quiz.status)}`}>{statusText(quiz.status)}</span></div><p className="mt-1 truncate text-xs text-slate-400">Từ: {quiz.document}</p><div className="mt-2 flex gap-4 text-[11px] text-slate-400"><span className="flex items-center gap-1"><ListChecks size={13} />{quiz.questions} câu</span><span className="flex items-center gap-1"><Clock3 size={13} />{quiz.duration} phút</span>{quiz.bestScore && <span className="font-bold text-emerald-600">Điểm cao nhất: {quiz.bestScore}%</span>}</div></div>
              <button disabled={quiz.status === 'processing'} onClick={startQuiz} className="rounded-xl border border-indigo-200 px-4 py-2.5 text-xs font-extrabold text-indigo-600 transition hover:bg-indigo-600 hover:text-white disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300">{quiz.status === 'completed' ? 'Làm lại' : quiz.status === 'processing' ? 'Đang tạo' : 'Bắt đầu'}</button>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
