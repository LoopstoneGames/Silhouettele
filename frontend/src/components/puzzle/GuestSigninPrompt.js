import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LogIn, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const signinHeading = (stats) => {
  if (stats.current_streak > 2) return `Don't lose your ${stats.current_streak}-day streak!`;
  if (stats.puzzles_solved > 0) {
    return `${stats.puzzles_solved} puzzle${stats.puzzles_solved > 1 ? "s" : ""} solved! Keep going.`;
  }
  return "Sign in to save your progress";
};

export const GuestSigninPrompt = ({ show, stats }) => {
  const navigate = useNavigate();
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          data-testid="guest-signin-prompt"
          className="rounded-2xl border border-primary/20 bg-primary/5 overflow-hidden"
        >
          {stats.current_streak > 0 && (
            <div className="bg-orange-500/10 border-b border-orange-500/20 px-4 py-2 flex items-center justify-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />
              <p className="text-xs font-semibold text-orange-600 dark:text-orange-400">
                Your {stats.current_streak}-day streak is only saved on this device!
              </p>
            </div>
          )}
          <div className="p-5 text-center space-y-3">
            <div className="space-y-1">
              <p className="font-heading font-bold text-base">
                {signinHeading(stats)}
              </p>
              <p className="text-sm text-muted-foreground">
                {stats.current_streak > 0
                  ? "Secure your streak, earn badges, and compete with friends."
                  : "Track streaks, earn badges, compete on leaderboards, and add friends."}
              </p>
            </div>
            <Button
              onClick={() => navigate("/login")}
              className="rounded-full gap-2 font-semibold px-6"
              data-testid="guest-signin-btn"
            >
              <LogIn className="w-4 h-4" />
              Sign in with Google
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
