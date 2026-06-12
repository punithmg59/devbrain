import {
  Brain,
  Bug,
  Code,
  Github,
  Lock,
  Shield,
  Zap,
} from "lucide-react";
import { authService } from "../services/authService";
import useAuthStore from "../hooks/useAuthStore";
import { Link } from "react-router-dom";

const features = [
  {
    icon: Zap,
    title: "Impact Radar",
    description:
      "Live now — trace dependency graphs and see what breaks before you ship a change",
  },
  {
    icon: Brain,
    title: "Engineering Memory",
    description: "Institutional knowledge that never leaves",
  },
  {
    icon: Code,
    title: "Smart Prompts",
    description: "AI code that fits your system perfectly",
  },
  {
    icon: Shield,
    title: "AI Validator",
    description: "Catch AI mistakes before production",
  },
  {
    icon: Bug,
    title: "Debug Intelligence",
    description: "Root cause in minutes not hours",
  },
  {
    icon: Lock,
    title: "Security Scanner",
    description: "Ship safe, stay compliant",
  },
];

export default function HomePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <span className="text-xl font-bold">DevBrain</span>
        {!user && (
          <button
            onClick={() => authService.loginWithGitHub()}
            className="flex items-center gap-2 px-4 py-2 bg-white text-gray-900 rounded-lg font-medium hover:bg-gray-100 transition-colors"
          >
            <Github className="w-4 h-4" />
            Sign in with GitHub
          </button>
        )}
        {user && (
          <Link
            to="/dashboard"
            className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
          >
            Dashboard →
          </Link>
        )}
      </nav>

      <section className="flex flex-col items-center text-center px-6 pt-24 pb-20">
        <span className="px-3 py-1 text-xs font-medium bg-purple-600/20 text-purple-400 rounded-full border border-purple-500/30 mb-6">
          AI Engineering Intelligence
        </span>
        <h1 className="text-4xl md:text-6xl font-bold max-w-4xl leading-tight mb-6">
          Understand, Validate &amp; Debug AI-Generated Code
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mb-10">
          DevBrain is the intelligence layer above your AI coding tools. Connect your repo
          and get instant architecture understanding.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          {user ? (
            <Link
              to="/dashboard"
              className="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
            >
              Go to Dashboard →
            </Link>
          ) : (
            <>
              <button
                onClick={() => authService.loginWithGitHub()}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
              >
                <Github className="w-5 h-5" />
                Connect GitHub Repo
              </button>
              <button className="px-6 py-3 border border-gray-600 hover:border-gray-500 rounded-lg font-medium text-gray-300 transition-colors">
                See how it works
              </button>
            </>
          )}
        </div>
      </section>

      <section className="px-6 pb-24 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl hover:border-purple-500/40 transition-colors"
            >
              <Icon className="w-8 h-8 text-purple-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">{title}</h3>
              <p className="text-gray-400 text-sm">{description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
