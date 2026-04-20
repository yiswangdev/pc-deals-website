"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

interface AlertConfig {
  enabled: boolean;
  categories: string[];
}

interface User {
  email: string;
  alert_config?: AlertConfig;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const API = process.env.NEXT_PUBLIC_API_URL || "/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    const storedToken = localStorage.getItem("pcdeals_token");

    if (!storedToken) {
      setUser(null);
      setToken(null);
      return;
    }

    try {
      const res = await fetch(`${API}/me`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch current user");
      }

      const data = await res.json();

      setToken(storedToken);
      setUser(data);

      localStorage.setItem("pcdeals_email", data.email);
    } catch (err) {
      console.error("Auth refresh failed:", err);
      localStorage.removeItem("pcdeals_token");
      localStorage.removeItem("pcdeals_email");
      setUser(null);
      setToken(null);
    }
  };

  useEffect(() => {
    const init = async () => {
      await refreshUser();
      setLoading(false);
    };

    init();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }

    const data = await res.json();

    localStorage.setItem("pcdeals_token", data.access_token);
    localStorage.setItem("pcdeals_email", data.user?.email || email);

    setToken(data.access_token);
    setUser(data.user || { email });

    await refreshUser();
  };

  const register = async (email: string, password: string) => {
    const res = await fetch(`${API}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }

    const data = await res.json();

    localStorage.setItem("pcdeals_token", data.access_token);
    localStorage.setItem("pcdeals_email", data.user?.email || email);

    setToken(data.access_token);
    setUser(data.user || { email });

    await refreshUser();
  };

  const logout = () => {
    localStorage.removeItem("pcdeals_token");
    localStorage.removeItem("pcdeals_email");
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
