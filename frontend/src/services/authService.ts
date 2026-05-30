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
    } catch {
      return null;
    }
  },

  logout: async () => {
    await API.post("/api/auth/logout");
    window.location.href = "/";
  },
};

export default API;
