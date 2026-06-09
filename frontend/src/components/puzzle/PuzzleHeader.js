import { MAX_GUESSES } from "@/hooks/useDailyPuzzle";

const pipClass = (g) => {
  if (g?.is_correct) return "w-7 bg-emerald-500";
  if (g) return "w-7 bg-muted-foreground/40";
  return "w-4 bg-border";
};

export const PuzzleHeader = ({ date, guesses, gameOver, used }) => (
  <div className="text-center space-y-3">
    <p className="font-technical text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
      {date}
    </p>
    <h1 className="font-heading font-black text-3xl sm:text-4xl tracking-tight" data-testid="puzzle-title">
      Guess the Building
    </h1>
    {/* Progress pips */}
    <div className="flex items-center justify-center gap-1.5 pt-1">
      {Array.from({ length: MAX_GUESSES }).map((_, i) => (
        <span
          key={`pip-${i}`}
          className={`h-1.5 rounded-full transition-all duration-300 ${pipClass(guesses?.[i])}`}
        />
      ))}
    </div>
    {!gameOver && (
      <p className="font-technical text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
        Guess {used + 1} / {MAX_GUESSES}
      </p>
    )}
  </div>
);
