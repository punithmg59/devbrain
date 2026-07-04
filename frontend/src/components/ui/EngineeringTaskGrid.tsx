import { Trash2, GitMerge, Plus, Bug, Building2, Zap, Shield, FlaskConical } from "lucide-react";

interface EngineeringTaskGridProps {
  onSelectTask: (query: string) => void;
}

const engineeringTasks = [
  {
    icon: Trash2,
    title: "Delete Code Safely",
    description: "Understand impact before removing",
    query: "What breaks if I delete this code?",
  },
  {
    icon: GitMerge,
    title: "Refactor Feature",
    description: "Plan safe refactoring strategies",
    query: "How should I refactor this feature safely?",
  },
  {
    icon: Plus,
    title: "Add New Feature",
    description: "Find where to add functionality",
    query: "Where should I add this new feature?",
  },
  {
    icon: Bug,
    title: "Investigate Bug",
    description: "Trace and understand issues",
    query: "What could be causing this bug?",
  },
  {
    icon: Building2,
    title: "Explain Architecture",
    description: "Understand system design",
    query: "Explain the architecture of this repository",
  },
  {
    icon: Zap,
    title: "Improve Performance",
    description: "Identify optimization opportunities",
    query: "How can I improve performance here?",
  },
  {
    icon: Shield,
    title: "Security Review",
    description: "Find security vulnerabilities",
    query: "Are there any security issues here?",
  },
  {
    icon: FlaskConical,
    title: "Generate Tests",
    description: "Create comprehensive test coverage",
    query: "Generate tests for this code",
  },
];

export default function EngineeringTaskGrid({ onSelectTask }: EngineeringTaskGridProps) {
  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight mb-6">Engineering Tasks</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {engineeringTasks.map((task) => (
          <button
            key={task.title}
            onClick={() => onSelectTask(task.query)}
            className="group text-left bg-gradient-to-br from-gray-900/60 to-gray-800/40 border border-gray-800/50 hover:border-purple-500/30 hover:from-purple-900/20 hover:to-blue-900/20 rounded-2xl p-5 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10 hover:-translate-y-0.5"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-200">
              <task.icon className="w-5 h-5 text-gray-400 group-hover:text-purple-400 transition-colors" />
            </div>
            <h3 className="font-semibold text-gray-200 mb-1 group-hover:text-white transition-colors">{task.title}</h3>
            <p className="text-sm text-gray-500 group-hover:text-gray-400 transition-colors">{task.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
