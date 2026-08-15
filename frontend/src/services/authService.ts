import axios from "axios";

const apiUrl = import.meta.env.VITE_API_URL || "";

const API = axios.create({
  baseURL: apiUrl,
  withCredentials: true,
});

if (typeof window !== "undefined") {
  console.log(
    "[APP_BOOT] [AuthService] API client initialized. withCredentials:",
    API.defaults.withCredentials,
    "baseURL:",
    apiUrl || "(same-origin)"
  );
}

// Request interceptor
API.interceptors.request.use(
  (config) => {
    console.log(
      `[API] ${config.method?.toUpperCase()} ${config.baseURL || ""}${config.url}`
    );
    return config;
  },
  (error) => {
    console.error("[API] Request configuration error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor
API.interceptors.response.use(
  (response) => {
    console.log(
      `[API] ${response.status} ${response.config.url}`
    );
    return response;
  },
  (error) => {
    const status = error.response ? error.response.status : "NETWORK_ERROR";
    const url = error.config ? error.config.url : "unknown";
    console.warn(`[API] ${status} on ${url}:`, error.message);
    return Promise.reject(error);
  }
);

export const authService = {
  loginWithGitHub: () => {
    const targetUrl = `${apiUrl}/api/auth/github`;
    console.log(`[AUTH_BOOT] Redirecting to GitHub OAuth login: ${targetUrl}`);
    window.location.href = targetUrl;
  },

  getCurrentUser: async () => {
    try {
      console.log("[AUTH_BOOT] Requesting current user from /api/auth/me...");
      const res = await API.get("/api/auth/me");
      // Check for valid JSON object response rather than HTML SPA fallback
      if (
        typeof res.data === "string" ||
        !res.data ||
        typeof res.data !== "object" ||
        !("id" in res.data)
      ) {
        console.warn(
          "[AUTH_BOOT] Received non-JSON or invalid user object from /api/auth/me:",
          res.data
        );
        return null;
      }
      return res.data;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr.response && axiosErr.response.status === 401) {
        console.log("[AUTH_BOOT] User session unauthenticated (401).");
      } else {
        console.warn("[AUTH_BOOT] /api/auth/me request failed:", err);
      }
      return null;
    }
  },

  logout: async () => {
    console.log("[AUTH_BOOT] Logging out user...");
    try {
      await API.post("/api/auth/logout");
    } catch (err) {
      console.warn("[AUTH_BOOT] Logout API request error:", err);
    } finally {
      window.location.href = "/";
    }
  },
};

export default API;
