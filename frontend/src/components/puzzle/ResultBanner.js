import { Button } from "@/components/ui/button";
import { Share2, PartyPopper, Frown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const ResultBanner = ({ gameOver, isSolved, guessesUsed, onShare }) => (
  <AnimatePresence>
    {gameOver && (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 26 }}
        className={`rounded-2xl border p-5 text-center space-y-3 ${
          isSolved
            ? "border-emerald-500/30 bg-emerald-500/10"
            : "border-rose-500/30 bg-rose-500/10"
        }`}
        data-testid={isSolved ? "success-message" : "failure-message"}
      >
        <div className="flex items-center justify-center gap-2">
          {isSolved ? (
            <PartyPopper className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <Frown className="w-5 h-5 text-rose-500" />
          )}
          <p className={`font-heading font-bold text-lg ${isSolved ? "text-emerald-600 dark:text-emerald-400" : "text-rose-500"}`}>
            {isSolved
              ? `Solved in ${guessesUsed} ${guessesUsed === 1 ? "guess" : "guesses"}!`
              : "Better luck tomorrow!"}
          </p>
        </div>
        <Button
          onClick={onShare}
          className="rounded-full gap-2 font-semibold px-6"
          data-testid={isSolved ? "share-results-btn" : "share-results-btn-failed"}
        >
          <Share2 className="w-4 h-4" />
          Share Result
        </Button>
      </motion.div>
    )}
  </AnimatePresence>
);
