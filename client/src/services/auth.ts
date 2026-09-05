import { apiClient, TOKEN_STORAGE_KEY } from "./apiClient";

export interface User {
  id: string;
  email: string;
  fullName?: string;
  role: string;
  isActive: boolean;
  avatarUrl?: string;
  bio?: string;
  themePreference?: string;
  createdAt: string;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export const authService = {
  getToken(): string | null {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  },

  setToken(token: string): void {
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } catch {
      // Ignore
    }
  },

  clearToken(): void {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // Ignore
    }
  },

  isAuthenticated(): boolean {
    return Boolean(this.getToken());
  },

  async register(email: string, password: string, fullName?: string): Promise<AuthResponse> {
    const response = await apiClient.post("/auth/register", {
      email,
      password,
      full_name: fullName,
    });
    const data = response.data;
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return {
      accessToken: data.access_token,
      tokenType: data.token_type,
      expiresIn: data.expires_in,
      user: {
        id: data.user.id,
        email: data.user.email,
        fullName: data.user.full_name,
        role: data.user.role,
        isActive: data.user.is_active,
        createdAt: data.user.created_at,
      },
    };
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post("/auth/login", {
      email,
      password,
    });
    const data = response.data;
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return {
      accessToken: data.access_token,
      tokenType: data.token_type,
      expiresIn: data.expires_in,
      user: {
        id: data.user.id,
        email: data.user.email,
        fullName: data.user.full_name,
        role: data.user.role,
        isActive: data.user.is_active,
        createdAt: data.user.created_at,
      },
    };
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get("/auth/me");
    const u = response.data;
    return {
      id: u.id,
      email: u.email,
      fullName: u.full_name,
      role: u.role,
      isActive: u.is_active,
      avatarUrl: u.avatar_url,
      bio: u.bio,
      themePreference: u.theme_preference,
      createdAt: u.created_at,
    };
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      this.clearToken();
    }
  },
};
