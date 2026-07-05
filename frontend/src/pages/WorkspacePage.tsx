import { useMemo } from "react";
import EmptyState from "../components/change-intelligence/EmptyState";
import LoadingState from "../components/change-intelligence/LoadingState";
import RecentQuestions from "../components/change-intelligence/RecentQuestions";
import RepositoryHeader from "../components/engineering-decision/RepositoryHeader";
import EngineeringQueryBar from "../components/engineering-decision/EngineeringQueryBar";
import EngineeringDecisionView from "../components/EngineeringDecisionView";
import { useChangeIntelligence } from "../hooks/useChangeIntelligence";

type WorkspacePageProps = {
  repoId?: string;
};


export default function WorkspacePage({ repoId: propRepoId }: WorkspacePageProps) {
  const repoId = propRepoId ?? import.meta.env.VITE_REPO_ID ?? "demo-repo";
  const {
    question,
    setQuestion,
    loading,
    error,
    report,
    timing,
    recentQuestions,
    submitQuestion,
    cancelRequest,
    clearReport,
    pipelineStatus,
  } = useChangeIntelligence({ repoId });

  const handleSubmit = () => {
    console.log("WorkspacePage: handleSubmit", { loading, question, repoId });
    if (loading) {
      cancelRequest();
      return;
    }

    void submitQuestion();
  };

  const handleCopyReport = () => {
    if (report) {
      navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    }
  };

  const handleShareReport = () => {
    // Implement share functionality
    console.log("Share report");
  };

  const handleBack = () => {
    clearReport();
  };

  const statusSummary = useMemo(() => {
    if (!recentQuestions.length) return "No questions yet";
    return `${recentQuestions.length} recent question${recentQuestions.length === 1 ? "" : "s"}`;
  }, [recentQuestions]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_35%),linear-gradient(135deg,_#05070b_0%,_#090b10_40%,_#0d1117_100%)] px-4 py-6 text-slate-100 sm:px-6 lg:px-8 lg:py-8">
      {report ? (
        <EngineeringDecisionView
          report={report}
          timing={timing ?? undefined}
          onCopyReport={handleCopyReport}
          onShare={handleShareReport}
          onBack={handleBack}
        />
      ) : (
        <div className="min-h-screen bg-[#09090b]">
          {/* Repository Header */}
          <RepositoryHeader
            repositoryName="devbrain"
            branch="main"
            analysisStatus="analyzed"
            repositoryHealth="healthy"
            lastAnalysis="2 hours ago"
          />

          {/* Main Content */}
          <div className="max-w-[90%] mx-auto px-6 py-12">
            <div className="max-w-3xl mx-auto space-y-8">
              {/* Query Bar */}
              <EngineeringQueryBar
                value={question}
                onChange={setQuestion}
                onSubmit={handleSubmit}
                loading={loading}
                suggestions={recentQuestions}
              />

              {/* Loading State */}
              {loading && (
                <div className="space-y-4">
                  <LoadingState />
                  <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-4 text-sm text-gray-400">
                    {pipelineStatus}
                  </div>
                </div>
              )}

              {/* Error State */}
              {error && (
                <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-6 text-sm text-red-200">
                  <p className="font-semibold">{error.message}</p>
                  <p className="mt-2 text-red-300/80">Code: {error.code}</p>
                </div>
              )}

              {/* Empty State */}
              {!loading && !error && !report && (
                <EmptyState />
              )}

              {/* Recent Questions */}
              {recentQuestions.length > 0 && !loading && !error && (
                <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-6">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Recent Questions</h3>
                    <span className="text-sm text-gray-400">{statusSummary}</span>
                  </div>
                  <RecentQuestions questions={recentQuestions} onSelect={setQuestion} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
