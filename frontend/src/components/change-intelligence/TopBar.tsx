import { ArrowUpRight, GitBranch, ShieldCheck, Sparkles } from "lucide-react";

type TopBarProps = {
  repositoryName: string;
  branch: string;
  repositoryStatus: string;
  analyzeStatus: string;
};

export default function TopBar({ repositoryName, branch, repositoryStatus, analyzeStatus }: TopBarProps) {
  return (
    <header className="rounded-[28px] border border-white/10 bg-[#0d0f14]/70 px-5 py-4 shadow-[0_18px_50px_rgba(0,0,0,0.22)] backdrop-blur sm:px-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-200/90 via-slate-100 to-slate-400 text-sm font-semibold text-slate-950">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Repository</p>
            <div className="flex items-center gap-2 text-base font-semibold text-white">
              <span>{repositoryName}</span>
              <ArrowUpRight className="h-4 w-4 text-slate-500" />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { label: "Current branch", value: branch },
            { label: "Repository status", value: repositoryStatus },
            { label: "Analyze status", value: analyzeStatus },
          ].map((item) => (
            <div
              key={item.label}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300"
            >
              {item.label === "Current branch" ? (
                <GitBranch className="h-4 w-4 text-slate-500" />
              ) : (
                <ShieldCheck className="h-4 w-4 text-slate-500" />
              )}
              <span className="text-slate-200">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
