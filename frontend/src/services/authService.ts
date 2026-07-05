import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
});

export const authService = {
  loginWithGitHub: () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/github`;
  },

  getCurrentUser: async () => {
    try {
      const res = await API.get("/api/auth/me");
      return res.data;
    } catch (err: any) {
      if (import.meta.env.DEV && err?.response?.status === 401) {
        try {
          const devRes = await API.post("/api/auth/dev-login");
          return devRes.data;
        } catch {
          return null;
        }
      }
      return null;
    }
  },

  logout: async () => {
    await API.post("/api/auth/logout");
    window.location.href = "/";
  },

  checkGitHubToken: async () => {
    try {
      const res = await API.get("/api/auth/github-token-status");
      return res.data.has_token;
    } catch {
      return false;
    }
  },
};

export default API;
