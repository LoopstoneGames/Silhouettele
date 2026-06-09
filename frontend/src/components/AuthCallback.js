import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Landmark } from "lucide-react";

export const AuthCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Supabase JS client handles token exchange automatically via onAuthStateChange.
    // Just wait a moment and redirect home.
    const timer = setTimeout(() => navigate("/", { replace: true }), 1500);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background">
      <Landmark className="w-10 h-10 animate-pulse text-foreground" />
      <p className="font-heading text-sm text-muted-foreground uppercase tracking-widest">
        Authenticating...
      </p>
    </div>
  );
};
