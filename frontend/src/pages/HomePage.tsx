import {
  Github,
  ArrowRight,
  GitBranch,
  FileCode,
  Layers,
  Radio,
} from "lucide-react";
import { authService } from "../services/authService";
import useAuthStore from "../hooks/useAuthStore";
import { Link } from "react-router-dom";

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

      {/* Hero Section */}
      <section className="flex flex-col items-center text-center px-6 pt-24 pb-20">
        <span className="px-3 py-1 text-xs font-medium bg-purple-600/20 text-purple-400 rounded-full border border-purple-500/30 mb-6">
          Repository Intelligence
        </span>
        <h1 className="text-4xl md:text-6xl font-bold max-w-4xl leading-tight mb-6">
          Understand Your Codebase Before You Change It
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mb-10">
          DevBrain analyzes your GitHub repository to map functions, classes, API routes, and
          dependencies—so you can understand the impact of a change before touching the code.
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
                Connect GitHub Repository
              </button>
              <button className="px-6 py-3 border border-gray-600 hover:border-gray-500 rounded-lg font-medium text-gray-300 transition-colors">
                See How It Works
              </button>
            </>
          )}
        </div>
      </section>

      {/* How It Works Section */}
      <section className="px-6 py-20 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">How DevBrain Works</h2>
        <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
          Get deep understanding of your repository in four simple steps
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center font-bold">
                1
              </div>
              <Github className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Sign up with GitHub</h3>
            <p className="text-gray-400 text-sm">
              Create your DevBrain account securely with your GitHub account.
            </p>
          </div>
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center font-bold">
                2
              </div>
              <GitBranch className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Connect your repository</h3>
            <p className="text-gray-400 text-sm">
              Choose the GitHub repository you want DevBrain to understand.
            </p>
          </div>
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center font-bold">
                3
              </div>
              <FileCode className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Analyze your repository</h3>
            <p className="text-gray-400 text-sm">
              Click Analyze and let DevBrain inspect the repository. Show real analysis
              progress from the backend.
            </p>
          </div>
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center font-bold">
                4
              </div>
              <Layers className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Explore & understand</h3>
            <p className="text-gray-400 text-sm">
              Explore functions, classes, API routes, dependencies, and use Impact Radar to
              understand what changes can affect.
            </p>
          </div>
        </div>
      </section>

      {/* Core Product Section */}
      <section className="px-6 py-20 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">One Codebase. Deep Understanding.</h2>
        <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
          DevBrain focuses on repository and codebase intelligence
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl hover:border-purple-500/40 transition-colors">
            <FileCode className="w-8 h-8 text-purple-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Functions</h3>
            <p className="text-gray-400 text-sm">
              Find and understand functions across your repository.
            </p>
          </div>
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl hover:border-purple-500/40 transition-colors">
            <Layers className="w-8 h-8 text-purple-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Classes</h3>
            <p className="text-gray-400 text-sm">
              Explore classes and understand how they connect to the rest of your codebase.
            </p>
          </div>
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl hover:border-purple-500/40 transition-colors">
            <GitBranch className="w-8 h-8 text-purple-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">API Routes</h3>
            <p className="text-gray-400 text-sm">
              Discover API endpoints and understand the code behind each route.
            </p>
          </div>
        </div>
        <p className="text-center text-gray-400 max-w-2xl mx-auto">
          Impact Radar connects these pieces to help you understand the consequences of code
          changes.
        </p>
      </section>

      {/* Impact Radar Section */}
      <section className="px-6 py-20 max-w-6xl mx-auto">
        <div className="p-8 md:p-12 bg-gradient-to-br from-purple-900/20 to-gray-900/50 border border-purple-500/30 rounded-2xl">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="flex-1">
              <Radio className="w-12 h-12 text-purple-500 mb-4" />
              <h2 className="text-3xl font-bold mb-4">See the Impact Before You Change the Code</h2>
              <p className="text-gray-400 mb-6">
                Impact Radar traces relationships between functions, classes, API routes, files,
                and dependencies to help you understand what could be affected by a change.
              </p>
              <div className="flex flex-wrap gap-3">
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Affected Functions
                </span>
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Affected Classes
                </span>
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Affected API Routes
                </span>
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Related Files
                </span>
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Dependencies
                </span>
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm border border-purple-500/30">
                  Callers / References
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product Workflow Visual */}
      <section className="px-6 py-20 max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">From Repository to Intelligence</h2>
        <div className="flex flex-col md:flex-row items-center justify-center gap-4">
          <div className="flex flex-col items-center">
            <Github className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">GitHub</span>
          </div>
          <ArrowRight className="w-6 h-6 text-gray-600 hidden md:block" />
          <div className="w-6 h-0.5 bg-gray-600 md:hidden" />
          <div className="flex flex-col items-center">
            <GitBranch className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">Connect Repository</span>
          </div>
          <ArrowRight className="w-6 h-6 text-gray-600 hidden md:block" />
          <div className="w-6 h-0.5 bg-gray-600 md:hidden" />
          <div className="flex flex-col items-center">
            <FileCode className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">Analyze</span>
          </div>
          <ArrowRight className="w-6 h-6 text-gray-600 hidden md:block" />
          <div className="w-6 h-0.5 bg-gray-600 md:hidden" />
          <div className="flex flex-col items-center">
            <Layers className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">Repository Intelligence</span>
          </div>
          <ArrowRight className="w-6 h-6 text-gray-600 hidden md:block" />
          <div className="w-6 h-0.5 bg-gray-600 md:hidden" />
          <div className="flex flex-col items-center">
            <Radio className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">Explore Repository</span>
          </div>
          <ArrowRight className="w-6 h-6 text-gray-600 hidden md:block" />
          <div className="w-6 h-0.5 bg-gray-600 md:hidden" />
          <div className="flex flex-col items-center">
            <Radio className="w-10 h-10 text-purple-500 mb-2" />
            <span className="text-sm text-gray-400">Impact Radar</span>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 py-20 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to understand your codebase?</h2>
        <p className="text-gray-400 mb-8">
          Connect your GitHub repository and start exploring with Impact Radar.
        </p>
        {user ? (
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-4 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
          >
            Go to Dashboard
            <ArrowRight className="w-5 h-5" />
          </Link>
        ) : (
          <button
            onClick={() => authService.loginWithGitHub()}
            className="inline-flex items-center gap-2 px-8 py-4 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
          >
            <Github className="w-5 h-5" />
            Connect GitHub Repository
          </button>
        )}
      </section>
    </div>
  );
}
