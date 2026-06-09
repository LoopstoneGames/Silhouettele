import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { puzzleAPI, buildingAPI } from "@/lib/api";
import { getGuestStats, recordGuestSolve, recordGuestFail } from "@/lib/guestStats";
import { logError } from "@/lib/logger";
import { toast } from "sonner";
import { Navigation } from "lucide-react";

export const MAX_GUESSES = 6;

/**
 * Encapsulates all Daily Puzzle game state, data loading and guess/share handlers.
 * Keeps the page component purely presentational.
 */
export function useDailyPuzzle() {
  const { user } = useAuth();
  const [puzzle, setPuzzle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [shakeGuess, setShakeGuess] = useState(false);
  const [guestStats, setGuestStats] = useState(() => getGuestStats());
  const searchTimeout = useRef(null);

  const loadPuzzle = useCallback(async () => {
    try {
      const res = await puzzleAPI.getToday();
      setPuzzle(res.data);
    } catch (err) {
      if (err.response?.status === 401) return;
      toast.error("Failed to load puzzle");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPuzzle();
  }, [loadPuzzle]);

  const handleSearch = (value) => {
    setSearchQuery(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (value.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      try {
        const res = await buildingAPI.search(value);
        const guessedIds = new Set(puzzle?.guesses?.map((g) => g.guess_building_id) || []);
        const filtered = res.data.filter((b) => !guessedIds.has(b.building_id));
        setSearchResults(filtered);
        setShowDropdown(filtered.length > 0);
      } catch (err) {
        logError("Building search failed:", err);
        setSearchResults([]);
      }
    }, 250);
  };

  const handleGuess = async (building) => {
    setSubmitting(true);
    setShowDropdown(false);
    setSearchQuery("");
    try {
      const res = await puzzleAPI.submitGuess(building.building_id);
      setPuzzle((prev) => ({ ...prev, ...res.data }));
      if (res.data.is_solved) {
        toast.success("Correct! Well done!");
        if (!user) {
          const updated = recordGuestSolve(res.data.guess?.puzzle_date || puzzle.puzzle_date, res.data.guesses_used);
          setGuestStats(updated);
        }
      } else if (res.data.is_failed) {
        toast.error("Out of guesses! Better luck tomorrow.");
        if (!user) {
          const updated = recordGuestFail(res.data.guess?.puzzle_date || puzzle.puzzle_date);
          setGuestStats(updated);
        }
      } else {
        setShakeGuess(true);
        setTimeout(() => setShakeGuess(false), 500);
        toast("Not quite! Check the direction hint.", { icon: <Navigation className="w-4 h-4" /> });
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit guess");
    } finally {
      setSubmitting(false);
    }
  };

  const gameOver = !!(puzzle && (puzzle.is_solved || puzzle.is_failed));
  const used = puzzle?.guesses?.length || 0;

  return {
    user,
    puzzle,
    loading,
    gameOver,
    used,
    searchQuery,
    searchResults,
    submitting,
    showDropdown,
    shakeGuess,
    guestStats,
    setShowDropdown,
    handleSearch,
    handleGuess,
  };
}
