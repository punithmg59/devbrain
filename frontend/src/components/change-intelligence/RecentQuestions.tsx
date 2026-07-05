type RecentQuestionsProps = {
  questions: string[];
  onSelect: (value: string) => void;
};

export default function RecentQuestions({ questions, onSelect }: RecentQuestionsProps) {
  if (!questions.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">Recent questions</h3>
      </div>
      <div className="divide-y divide-white/10 rounded-[24px] border border-white/10 bg-[#090b10]/70">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelect(question)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"
          >
            <span>{question}</span>
            <span className="text-xs uppercase tracking-[0.24em] text-slate-500">Open</span>
          </button>
        ))}
      </div>
    </div>
  );
}
