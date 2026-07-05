import { CornerDownLeft, Sparkles } from "lucide-react";

type QuestionCardProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
};

export default function QuestionCard({ value, onChange, onSubmit, placeholder }: QuestionCardProps) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      console.log("QuestionCard: keyboard submit");
      onSubmit();
    }
  };

  return (
    <div className="rounded-[28px] border border-white/10 bg-[#090b10]/70 p-4 shadow-[0_28px_70px_rgba(0,0,0,0.24)] sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Sparkles className="h-4 w-4 text-slate-500" />
          Ask DevBrain
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.24em] text-slate-500">
          Ctrl + Enter
        </div>
      </div>

      <label className="sr-only" htmlFor="workspace-question">
        Engineering change question
      </label>
      <textarea
        id="workspace-question"
        className="min-h-[140px] w-full resize-none rounded-2xl border border-white/10 bg-[#11141a]/90 px-4 py-4 text-base leading-7 text-slate-100 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-500/30"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-500">Understand, plan and safely execute software changes.</p>
        <button
          type="button"
          onClick={() => {
            console.log("QuestionCard: button submit");
            onSubmit();
          }}
          disabled={!value.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          <CornerDownLeft className="h-4 w-4" />
          Submit
        </button>
      </div>
    </div>
  );
}
