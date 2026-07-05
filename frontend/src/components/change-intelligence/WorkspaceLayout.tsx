import type { ReactNode } from "react";

type WorkspaceLayoutProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export default function WorkspaceLayout({ title, subtitle, children }: WorkspaceLayoutProps) {
  return (
    <section className="rounded-[32px] border border-white/10 bg-[#0d0f14]/80 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.28)] backdrop-blur xl:p-8">
      <div className="mb-8 max-w-3xl">
        <p className="mb-3 text-sm font-medium uppercase tracking-[0.24em] text-slate-500">Engineering workspace</p>
        <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h2>
        <p className="mt-3 text-sm leading-7 text-slate-400 sm:text-base">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}
