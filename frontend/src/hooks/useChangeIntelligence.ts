import { useCallback, useMemo, useRef, useState } from "react";
import { changeIntelligenceApi } from "../services/changeIntelligenceApi";
import type { ChangeIntelligenceResponse, EngineeringReport } from "../types/engineeringReport";

export type ChangeIntelligenceErrorCode =
  | "EMPTY_QUESTION"
  | "REPOSITORY_NOT_ANALYZED"
  | "NETWORK_ERROR"
  | "TIMEOUT"
  | "SERVER_ERROR"
  | "UNKNOWN_ERROR";

export interface ChangeIntelligenceError {
  code: ChangeIntelligenceErrorCode;
  message: string;
}

interface UseChangeIntelligenceOptions {
  repoId: string;
}

export function useChangeIntelligence({ repoId }: UseChangeIntelligenceOptions) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ChangeIntelligenceError | null>(null);
  const [report, setReport] = useState<EngineeringReport | null>(null);
  const [timing, setTiming] = useState<Record<string, number> | null>(null);
  const [recentQuestions, setRecentQuestions] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const resetError = useCallback(() => setError(null), []);

  const submitQuestion = useCallback(async (nextQuestion?: string) => {
    const normalizedQuestion = (nextQuestion ?? question).trim();
    console.log("useChangeIntelligence: submitQuestion", { normalizedQuestion, repoId, loading });

    if (!normalizedQuestion) {
      setError({ code: "EMPTY_QUESTION", message: "Please enter a question before submitting." });
      return;
    }

    if (loading) {
      abortRef.current?.abort();
    }

    setLoading(true);
    setError(null);
    setReport(null);
    setTiming(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response: ChangeIntelligenceResponse = await changeIntelligenceApi.analyze(repoId, normalizedQuestion);
      if (controller.signal.aborted) {
        return;
      }

      setReport(response.report ?? null);
      setTiming(response.timing ? Object.fromEntries(Object.entries(response.timing).filter(([, value]) => typeof value === "number")) : null);
      setRecentQuestions((previous) => [normalizedQuestion, ...previous].slice(0, 5));
      setQuestion("");
    } catch (err: unknown) {
      if (controller.signal.aborted) {
        return;
      }

      const message = err instanceof Error ? err.message : "Request failed";
      const status = (err as { response?: { status?: number } })?.response?.status;

      if (status === 400) {
        setError({ code: "EMPTY_QUESTION", message: "The question cannot be empty." });
      } else if (status === 404) {
        setError({ code: "SERVER_ERROR", message: "Repository not found." });
      } else if (status === 403) {
        setError({ code: "SERVER_ERROR", message: "You do not have access to this repository." });
      } else if (status === 400 && /not analyzed/i.test(message)) {
        setError({ code: "REPOSITORY_NOT_ANALYZED", message: "This repository must be analyzed before change intelligence can run." });
      } else if (message.includes("timeout") || message.includes("timed out")) {
        setError({ code: "TIMEOUT", message: "The request timed out. Please try again." });
      } else if (!navigator.onLine) {
        setError({ code: "NETWORK_ERROR", message: "You appear to be offline." });
      } else {
        setError({ code: "UNKNOWN_ERROR", message: "The request could not be completed. Please try again." });
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setLoading(false);
    }
  }, [loading, question, repoId]);

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }, []);

  const clearReport = useCallback(() => {
    setReport(null);
  }, []);

  const pipelineStatus = useMemo(() => {
    if (!timing) {
      return loading ? "Preparing change intelligence pipeline…" : "Awaiting review request";
    }

    const steps = [
      timing.intent_ms != null ? "Intent" : null,
      timing.evidence_ms != null ? "Evidence" : null,
      timing.reasoning_ms != null ? "Reasoning" : null,
      timing.report_ms != null ? "Report" : null,
    ].filter(Boolean) as string[];

    return steps.length ? `Pipeline: ${steps.join(" → ")}` : "Pipeline completed";
  }, [loading, timing]);

  return {
    question,
    setQuestion,
    loading,
    error,
    report,
    timing,
    recentQuestions,
    resetError,
    submitQuestion,
    cancelRequest,
    clearReport,
    pipelineStatus,
  };
}
