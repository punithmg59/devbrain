import API from "./authService";
import type { ChangeIntelligenceResponse } from "../types/engineeringReport";

export interface ChangeIntelligenceRequest {
  question: string;
}

export const changeIntelligenceApi = {
  analyze: async (repoId: string, question: string): Promise<ChangeIntelligenceResponse> => {
    console.log("changeIntelligenceApi: posting", { repoId, question });
    const response = await API.post(`/api/repos/${repoId}/change-intelligence`, {
      question,
    } satisfies ChangeIntelligenceRequest);
    console.log("changeIntelligenceApi: response", response.status, response.data);

    return response.data;
  },
};
