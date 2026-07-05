export default function LoadingState() {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-8">
      <div className="flex items-center gap-3">
        <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-slate-400" />
        <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-slate-400 [animation-delay:120ms]" />
        <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-slate-400 [animation-delay:240ms]" />
        <p className="ml-2 text-sm text-slate-400">Preparing the workspace foundation…</p>
      </div>
    </div>
  );
}
