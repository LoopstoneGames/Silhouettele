import { guessEmoji } from "@/lib/directions";
import { motion } from "framer-motion";
import { MAX_GUESSES } from "@/hooks/useDailyPuzzle";

const slotClass = (guess) => {
  if (guess?.is_correct) {
    return "border-emerald-500/40 bg-emerald-500/10 ring-1 ring-emerald-500/20 animate-pulse-glow";
  }
  if (guess) return "border-border bg-card";
  return "border-dashed border-border bg-transparent";
};

const FilledSlot = ({ guess }) => (
  <>
    <div className="flex items-center gap-3 min-w-0">
      <span className="font-technical text-xs text-muted-foreground w-4 shrink-0">{guess.guess_number}</span>
      <div className="min-w-0">
        <p className="font-semibold text-sm truncate">{guess.guess_building_name}</p>
        <p className="text-xs text-muted-foreground truncate">
          {guess.guess_building_city}, {guess.guess_building_country}
        </p>
      </div>
    </div>
    {guess.is_correct ? (
      <span className="flex items-center gap-1.5 shrink-0 text-emerald-600 dark:text-emerald-400 font-semibold text-sm">
        <span className="text-xl">{guessEmoji(guess)}</span>
        Found it!
      </span>
    ) : (
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-2xl leading-none" title={guess.direction}>{guessEmoji(guess)}</span>
        <span className="font-technical text-xs text-muted-foreground tabular-nums">
          {guess.distance_km.toLocaleString()} km
        </span>
      </div>
    )}
  </>
);

const EmptySlot = ({ position }) => (
  <div className="flex items-center gap-3 w-full">
    <span className="font-technical text-xs text-muted-foreground/30 w-4 shrink-0">{position}</span>
    <div className="h-2.5 flex-1 rounded-full bg-muted/60" />
  </div>
);

export const GuessGrid = ({ guesses, used, shakeGuess }) => (
  <div className="space-y-2.5" data-testid="guess-grid">
    {Array.from({ length: MAX_GUESSES }).map((_, i) => {
      const guess = guesses?.[i];
      const isLatest = guess && i === used - 1;
      return (
        <motion.div
          key={`slot-${i}`}
          initial={guess ? { opacity: 0, y: 12 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: guess ? 0.04 : 0, type: "spring", stiffness: 320, damping: 26 }}
          className={isLatest && shakeGuess ? "animate-shake" : ""}
        >
          <div
            className={`rounded-xl border flex items-center justify-between min-h-[58px] px-3.5 transition-colors ${slotClass(guess)}`}
            data-testid={`guess-slot-${i}`}
          >
            {guess ? <FilledSlot guess={guess} /> : <EmptySlot position={i + 1} />}
          </div>
        </motion.div>
      );
    })}
  </div>
);
