import { Network, Maximize2, ZoomIn, ZoomOut, Sparkles } from "lucide-react";

interface DiagramCanvasProps {
  /** Human-readable label of the currently selected category. */
  activeLabel: string;
}

/**
 * Center panel — the architecture diagram area. This sprint ships the framed,
 * empty-state canvas only (no graph rendering, no AI). The toolbar buttons are
 * presentational placeholders for the upcoming diagram engine.
 */
export default function DiagramCanvas({ activeLabel }: DiagramCanvasProps) {
  return (
    <div className="relative flex h-full flex-col bg-[#0a0a0c]">
      {/* Canvas toolbar */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 px-4">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-purple-400" />
          <span className="text-sm font-medium text-white">Architecture Diagram</span>
          <span className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-gray-400">
            {activeLabel}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {[ZoomOut, ZoomIn, Maximize2].map((Icon, i) => (
            <button
              key={i}
              type="button"
              disabled
              className="grid h-7 w-7 cursor-not-allowed place-items-center rounded-md text-gray-500 opacity-60"
              aria-hidden
            >
              <Icon className="h-4 w-4" />
            </button>
          ))}
        </div>
      </div>

      {/* Empty diagram surface */}
      <div className="relative flex-1 overflow-hidden">
        {/* Animated dotted grid */}
        <div className="absolute inset-0 bg-grid-dots animate-grid-pan opacity-70" />
        {/* Radial fade so the grid recedes toward the edges */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,#0a0a0c_85%)]" />

        {/* Centered empty state */}
        <div className="relative z-10 flex h-full items-center justify-center p-6">
          <div className="animate-fade-in-up flex max-w-md flex-col items-center text-center">
            <div className="relative mb-6">
              <div className="absolute inset-0 rounded-2xl bg-purple-500/20 blur-2xl" />
              <div className="relative grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <Network className="h-7 w-7 text-purple-300" />
              </div>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-white">No diagram yet</h2>
            <p className="mb-5 text-sm leading-relaxed text-gray-500">
              The architecture graph will render here. Pick a component category from the left to
              scope the view — interactive diagrams and AI explanations arrive in an upcoming sprint.
            </p>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs text-purple-300">
              <Sparkles className="h-3.5 w-3.5" />
              Coming soon
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
