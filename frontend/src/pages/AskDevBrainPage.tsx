import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import useAuthStore from "../hooks/useAuthStore";
import CommandCenter from "../components/ui/CommandCenter";
import SuggestionDropdown from "../components/ui/SuggestionDropdown";
import QuickActionChip, { quickActions } from "../components/ui/QuickActionChip";
import RepositoryInsights from "../components/ui/RepositoryInsights";
import RecentQuestions from "../components/ui/RecentQuestions";
import EngineeringTaskGrid from "../components/ui/EngineeringTaskGrid";

export default function AskDevBrainPage() {
  const user = useAuthStore((s) => s.user);
  const [query, setQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [recentQuestions, setRecentQuestions] = useState<string[]>([]);

  if (!user) return null;

  const handleAsk = () => {
    if (query.trim()) {
      setRecentQuestions((prev) => [query, ...prev].slice(0, 5));
      setQuery("");
      setShowSuggestions(false);
    }
  };

  const handleSelectSuggestion = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
  };

  const handleQuickAction = (action: string) => {
    setQuery(action);
  };

  const handleSelectTask = (taskQuery: string) => {
    setQuery(taskQuery);
  };

  return (
    <div className="min-h-screen bg-[#080808] text-white">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800/30 backdrop-blur-sm bg-[#080808]/80 sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="group p-2.5 rounded-xl hover:bg-gray-800/30 transition-all duration-200 hover:scale-105"
          >
            <ArrowLeft className="w-5 h-5 text-gray-500 group-hover:text-white transition-colors" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-xs font-bold">
              DB
            </div>
            <span className="text-lg font-semibold tracking-tight">Ask DevBrain</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {user.avatar_url && (
            <img
              src={user.avatar_url}
              alt={user.username}
              className="w-8 h-8 rounded-full border border-gray-800/50"
            />
          )}
          <span className="text-sm text-gray-400">{user.username}</span>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-16 space-y-12">
        {/* Hero */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
            Command Center
          </h1>
          <p className="text-xl text-gray-400 font-light">
            Ask anything about your codebase
          </p>
        </div>

        {/* Command Center with Suggestions */}
        <div className="relative">
          <CommandCenter
            value={query}
            onChange={setQuery}
            onSubmit={handleAsk}
          />
          <SuggestionDropdown
            visible={showSuggestions && query.length > 0}
            query={query}
            onSelect={handleSelectSuggestion}
          />
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action) => (
              <QuickActionChip
                key={action.label}
                icon={action.icon}
                label={action.label}
                onClick={() => handleQuickAction(action.label)}
              />
            ))}
          </div>
        </div>

        {/* Engineering Tasks */}
        <EngineeringTaskGrid onSelectTask={handleSelectTask} />

        {/* Repository Insights */}
        <RepositoryInsights
          language="TypeScript"
          analysisStatus="completed"
          functions={142}
          classes={38}
          services={12}
          largestFolder="src/app"
          mostConnectedService="AuthService"
          architectureHealth="Good"
        />

        {/* Recent Questions */}
        <RecentQuestions
          questions={recentQuestions}
          onAskQuestion={setQuery}
        />
      </main>
    </div>
  );
}
