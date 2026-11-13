import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const AuthContext = createContext(null);
const guest = { status: "guest", user: null, error: null };

export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "unknown", user: null, error: null });
  const current = useRef(state);
  const pending = useRef(null);
  const generation = useRef(0);
  const setAuth = useCallback((value) => { current.current = value; setState(value); }, []);
  const ensureSession = useCallback((force = false) => {
    if (pending.current) return pending.current;
    if (!force && ["authenticated", "guest"].includes(current.current.status)) return Promise.resolve(current.current.user);
    const started = generation.current;
    if (!current.current.user) setAuth({ status: "checking", user: null, error: null });
    pending.current = api.getMe().then((user) => {
      if (generation.current === started) setAuth({ status: "authenticated", user, error: null });
      return user;
    }).catch((error) => {
      if (generation.current === started) {
        setAuth([401, 403].includes(error.status) ? guest : { status: "error", user: null, error: "Não foi possível verificar seu acesso. Tente novamente." });
      }
      return null;
    }).finally(() => { pending.current = null; });
    return pending.current;
  }, [setAuth]);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible" && ["authenticated", "guest"].includes(current.current.status)) ensureSession(true);
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [ensureSession]);

  const login = async (credentials) => {
    generation.current += 1;
    const result = await api.login(credentials);
    setAuth({ status: "authenticated", user: result.user, error: null });
  };
  const acceptSession = (user) => {
    generation.current += 1;
    setAuth({ status: "authenticated", user, error: null });
  };
  const logout = async () => {
    generation.current += 1;
    try { await api.logout(); } catch (error) {
      if (![401, 403].includes(error.status)) throw error;
      await ensureSession(true);
      if (current.current.status !== "guest") throw error;
    }
    setAuth(guest);
  };
  const updateProfile = async (profile) => {
    try {
      const user = await api.updateProfile(profile);
      generation.current += 1;
      setAuth({ status: "authenticated", user, error: null });
      return user;
    } catch (error) {
      if ([401, 403].includes(error.status)) await ensureSession(true);
      throw error;
    }
  };
  const changePassword = async (passwords) => {
    try { return await api.changePassword(passwords); } catch (error) {
      if ([401, 403].includes(error.status)) await ensureSession(true);
      throw error;
    }
  };

  return <AuthContext.Provider value={{ ...state, ensureSession, login, logout, updateProfile, changePassword, acceptSession }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider is required.");
  return context;
}
