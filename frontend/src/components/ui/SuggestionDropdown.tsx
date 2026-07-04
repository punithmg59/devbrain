import { Trash2, Lock, Database } from "lucide-react";

interface Suggestion {
  icon: any;
  text: string;
}

interface SuggestionDropdownProps {
  visible: boolean;
  query: string;
  onSelect: (suggestion: string) => void;
}

const suggestionsByKeyword: Record<string, Suggestion[]> = {
  delete: [
    { icon: Trash2, text: "What breaks if I delete this function?" },
    { icon: Trash2, text: "What breaks if I delete this service?" },
    { icon: Trash2, text: "Show every dependency before deleting" },
  ],
  authentication: [
    { icon: Lock, text: "Explain authentication flow" },
    { icon: Lock, text: "Which middleware handles authentication?" },
    { icon: Lock, text: "Which APIs require authentication?" },
  ],
  auth: [
    { icon: Lock, text: "Explain authentication flow" },
    { icon: Lock, text: "Which middleware handles authentication?" },
    { icon: Lock, text: "Which APIs require authentication?" },
  ],
  database: [
    { icon: Database, text: "Show database relationships" },
    { icon: Database, text: "Which services use this table?" },
    { icon: Database, text: "Find unused tables" },
  ],
  db: [
    { icon: Database, text: "Show database relationships" },
    { icon: Database, text: "Which services use this table?" },
    { icon: Database, text: "Find unused tables" },
  ],
};

export default function SuggestionDropdown({ visible, query, onSelect }: SuggestionDropdownProps) {
  if (!visible || !query) return null;

  const lowerQuery = query.toLowerCase();
  let matchedSuggestions: Suggestion[] = [];

  for (const [keyword, suggestions] of Object.entries(suggestionsByKeyword)) {
    if (lowerQuery.includes(keyword)) {
      matchedSuggestions = suggestions;
      break;
    }
  }

  if (matchedSuggestions.length === 0) return null;

  return (
    <div className="absolute top-full left-0 right-0 mt-2 bg-gray-900/95 border border-gray-800/50 rounded-2xl shadow-2xl shadow-black/50 backdrop-blur-sm z-50 overflow-hidden">
      <div className="p-2">
        {matchedSuggestions.map((suggestion, index) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={index}
              onClick={() => onSelect(suggestion.text)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-gray-800/50 transition-colors text-left group"
            >
              <Icon className="w-5 h-5 text-gray-500 group-hover:text-purple-400 transition-colors" />
              <span className="text-gray-300 group-hover:text-white transition-colors">{suggestion.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
