import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authAPI } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { logError } from "@/lib/logger";

const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const syncUser = useCallback(async () => {
    try {
      const res = await authAPI.register();
      setUser(res.data);
      return res.data;
    } catch (err) {
      logError("Failed to sync user:", err);
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === "INITIAL_SESSION") {
          if (session) {
            await syncUser();
          }
          setLoading(false);
        } else if (event === "SIGNED_IN" && session) {
          await syncUser();
        } else if (event === "SIGNED_OUT") {
          setUser(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [syncUser]);

  const login = (userData) => setUser(userData);

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (err) {
      logError("Logout request failed:", err);
    }
    await supabase.auth.signOut();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
