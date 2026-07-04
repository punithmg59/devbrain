import { MessageSquare, Sparkles } from "lucide-react";

interface RecentQuestionsProps {
  questions?: string[];
  onAskQuestion?: (question: string) => void;
}

const placeholderQuestions = [
  "What breaks if I delete AuthService?",
  "Where should I implement Stripe payments?",
  "Explain the authentication flow",
];

export default function RecentQuestions({ questions = [], onAskQuestion }: RecentQuestionsProps) {
  if (questions.length === 0) {
    return (
      <div className="bg-gradient-to-br from-gray-900/40 to-gray-800/30 border border-gray-800/50 rounded-2xl p-8 backdrop-blur-sm text-center">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 flex items-center justify-center mx-auto mb-4">
          <MessageSquare className="w-6 h-6 text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-300 mb-2">No questions yet</h3>
        <p className="text-sm text-gray-500 mb-6">Ask DevBrain your first engineering question</p>
        <div className="space-y-2 max-w-md mx-auto">
          {placeholderQuestions.map((question, index) => (
            <button
              key={index}
              onClick={() => onAskQuestion?.(question)}
              className="w-full text-left px-4 py-3 bg-gray-900/50 border border-gray-800/50 hover:border-purple-500/30 hover:bg-purple-900/20 rounded-xl text-sm text-gray-400 hover:text-white transition-all duration-200"
            >
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                {question}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-gray-900/40 to-gray-800/30 border border-gray-800/50 rounded-2xl p-6 backdrop-blur-sm">
      <h3 className="text-lg font-semibold tracking-tight mb-4">Recent Questions</h3>
      <div className="space-y-2">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onAskQuestion?.(question)}
            className="w-full text-left px-4 py-3 bg-gray-900/30 border border-gray-800/50 hover:border-purple-500/30 hover:bg-purple-900/20 rounded-xl text-sm text-gray-400 hover:text-white transition-all duration-200"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
