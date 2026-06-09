import { Building2, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const GuessInput = ({
  searchQuery,
  searchResults,
  submitting,
  showDropdown,
  setShowDropdown,
  onSearch,
  onGuess,
}) => (
  <div className="relative" data-testid="guess-input-container">
    {showDropdown && (
      <div className="fixed inset-0 z-10" onClick={() => setShowDropdown(false)} aria-hidden="true" />
    )}
    <div className="relative z-20">
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
      <input
        type="text"
        placeholder="Type a building name…"
        value={searchQuery}
        onChange={(e) => onSearch(e.target.value)}
        onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
        disabled={submitting}
        data-testid="guess-search-input"
        className="w-full h-14 pl-12 pr-4 rounded-2xl bg-card border-2 border-border text-base font-medium placeholder:text-muted-foreground/70 outline-none transition-all focus:border-primary focus:ring-4 focus:ring-primary/10"
      />
    </div>
    <AnimatePresence>
      {showDropdown && searchResults.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          className="absolute z-20 mt-2 w-full max-h-72 overflow-y-auto thin-scroll rounded-2xl border border-border bg-popover shadow-xl p-1.5"
        >
          {searchResults.map((b) => (
            <button
              key={b.building_id}
              onClick={() => onGuess(b)}
              disabled={submitting}
              data-testid={`building-option-${b.building_id}`}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-accent transition-colors disabled:opacity-50"
            >
              <span className="grid place-items-center h-8 w-8 rounded-lg bg-muted shrink-0">
                <Building2 className="w-4 h-4 text-muted-foreground" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-sm truncate">{b.name}</p>
                <p className="text-xs text-muted-foreground truncate">{b.city}, {b.country}</p>
              </div>
            </button>
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  </div>
);
