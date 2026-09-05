import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

// Environment-configured API Base URL
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.NEXT_PUBLIC_API_BASE_URL ||
  "/api/v1";

// Centralized Axios client instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Storage token key
export const TOKEN_STORAGE_KEY = "khojai_access_token";

// Request interceptor: Attach Bearer JWT token if available
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // Ignore localStorage read errors in SSR or restricted contexts
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle 401 expiration and network failures
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; error?: string }>) => {
    if (error.response?.status === 401) {
      try {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        window.dispatchEvent(new CustomEvent("khojai:auth_expired"));
      } catch {
        // Ignore
      }
    }
    return Promise.reject(error);
  }
);

// Helper to extract clean user-facing error message
export function extractErrorMessage(error: unknown, fallback: string = "An unexpected error occurred."): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.error === "string") return data.error;
    if (error.response?.status === 429) return "Too many requests. Please wait a moment.";
    if (error.response?.status === 504) return "AI service timed out. Please try again.";
    if (error.message === "Network Error") return "Cannot connect to server. Please ensure the backend is running.";
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
