import { BookOpen, GitBranch, GitMerge, Trash2, Shield, FlaskConical, Plus, Zap } from "lucide-react";

interface QuickActionChipProps {
  icon: any;
  label: string;
  onClick: () => void;
}

export default function QuickActionChip({ icon: Icon, label, onClick }: QuickActionChipProps) {
  return (
    <button
      onClick={onClick}
      className="group flex items-center gap-2 px-4 py-2 bg-gray-900/40 border border-gray-800/50 hover:border-purple-500/30 hover:bg-purple-900/20 rounded-full text-sm text-gray-400 hover:text-white transition-all duration-200 hover:shadow-md hover:shadow-purple-500/10 hover:-translate-y-0.5"
    >
      <Icon className="w-4 h-4 group-hover:scale-110 transition-transform duration-200" />
      <span>{label}</span>
    </button>
  );
}

export const quickActions = [
  { icon: BookOpen, label: "Explain Repository" },
  { icon: GitBranch, label: "Find Dependencies" },
  { icon: GitMerge, label: "Safe Refactor" },
  { icon: Trash2, label: "Delete Analysis" },
  { icon: Zap, label: "Find Dead Code" },
  { icon: Shield, label: "Review Security" },
  { icon: FlaskConical, label: "Generate Tests" },
  { icon: Plus, label: "Plan New Feature" },
];
