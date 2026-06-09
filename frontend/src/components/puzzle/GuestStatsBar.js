import { Flame, Trophy, Target } from "lucide-react";
import { motion } from "framer-motion";

export const GuestStatsBar = ({ stats }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: 0.2 }}
    data-testid="guest-stats-bar"
    className="flex items-center justify-center gap-5 py-3 px-4 rounded-2xl border border-border bg-card/60"
  >
    <div className="flex items-center gap-1.5" title="Current streak">
      <Flame className={`w-4 h-4 ${stats.current_streak > 0 ? "text-orange-500" : "text-muted-foreground/40"}`} />
      <span className="font-technical text-sm font-medium tabular-nums">{stats.current_streak}</span>
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">streak</span>
    </div>
    <div className="w-px h-4 bg-border" />
    <div className="flex items-center gap-1.5" title="Puzzles solved">
      <Trophy className="w-3.5 h-3.5 text-muted-foreground/60" />
      <span className="font-technical text-sm font-medium tabular-nums">{stats.puzzles_solved}</span>
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">solved</span>
    </div>
    <div className="w-px h-4 bg-border" />
    <div className="flex items-center gap-1.5" title="Best streak">
      <Target className="w-3.5 h-3.5 text-muted-foreground/60" />
      <span className="font-technical text-sm font-medium tabular-nums">{stats.longest_streak}</span>
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">best</span>
    </div>
  </motion.div>
);
