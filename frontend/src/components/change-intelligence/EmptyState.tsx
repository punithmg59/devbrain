import { Compass } from "lucide-react";

export default function EmptyState() {
  return (
    <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
        <Compass className="h-5 w-5 text-slate-400" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-white">Initial workspace ready</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-7 text-slate-500">
        Ask a change-focused engineering question to begin shaping the workspace around it.
      </p>
    </div>
  );
}
