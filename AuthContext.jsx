import { createContext, useContext, useState, useCallback } from "react";
import api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("ss_user");
    return raw ? JSON.parse(raw) : null;
  });

  const login = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("ss_token", data.access_token);
    localStorage.setItem("ss_user", JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (profile) => {
    const { data } = await api.post("/auth/register", profile);
    localStorage.setItem("ss_token", data.access_token);
    localStorage.setItem("ss_user", JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("ss_token");
    localStorage.removeItem("ss_user");
    localStorage.removeItem("ss_parent_token");
    localStorage.removeItem("ss_parent_user");
    setUser(null);
  }, []);

  const updateProfile = useCallback(async (patch) => {
    const { data } = await api.patch("/auth/me", patch);
    localStorage.setItem("ss_user", JSON.stringify(data));
    setUser(data);
    return data;
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
