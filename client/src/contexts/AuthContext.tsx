import React, { createContext, useContext, useEffect, useState } from "react";
import { authService, User } from "@/services/auth";
import { toast } from "sonner";
import { extractErrorMessage } from "@/services/apiClient";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    if (!authService.isAuthenticated()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await authService.getMe();
      setUser(me);
    } catch {
      authService.clearToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();

    const onAuthExpired = () => {
      setUser(null);
      toast.info("Session expired. Please sign in again.");
    };

    window.addEventListener("khojai:auth_expired", onAuthExpired);
    return () => window.removeEventListener("khojai:auth_expired", onAuthExpired);
  }, []);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const res = await authService.login(email, pass);
      setUser(res.user);
      toast.success(`Welcome back, ${res.user.fullName || "Traveler"}`);
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to sign in."));
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, pass: string, fullName?: string) => {
    setIsLoading(true);
    try {
      const res = await authService.register(email, pass, fullName);
      setUser(res.user);
      toast.success("Account created successfully!");
    } catch (err) {
      toast.error(extractErrorMessage(err, "Registration failed."));
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      toast.success("Signed out.");
    } catch {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: Boolean(user),
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
