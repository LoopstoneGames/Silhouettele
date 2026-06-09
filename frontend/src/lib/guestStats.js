const STORAGE_KEY = "silhouettele_guest_stats";

const getStats = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

const saveStats = (stats) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
};

const defaultStats = () => ({
  puzzles_played: 0,
  puzzles_solved: 0,
  current_streak: 0,
  longest_streak: 0,
  total_guesses: 0,
  perfect_solves: 0,
  last_solved_date: null,
  last_played_date: null,
  solve_dates: [],
});

export const getGuestStats = () => {
  return getStats() || defaultStats();
};

export const recordGuestSolve = (puzzleDate, guessCount) => {
  const stats = getStats() || defaultStats();

  // Avoid double-counting
  if (stats.solve_dates?.includes(puzzleDate)) return stats;

  stats.puzzles_played += 1;
  stats.puzzles_solved += 1;
  stats.total_guesses += guessCount;
  if (guessCount === 1) stats.perfect_solves += 1;

  // Streak calc
  const yesterday = new Date();
  yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  const yesterdayStr = yesterday.toISOString().split("T")[0];

  if (stats.last_solved_date === yesterdayStr) {
    stats.current_streak += 1;
  } else if (stats.last_solved_date !== puzzleDate) {
    stats.current_streak = 1;
  }

  if (stats.current_streak > stats.longest_streak) {
    stats.longest_streak = stats.current_streak;
  }

  stats.last_solved_date = puzzleDate;
  stats.last_played_date = puzzleDate;
  stats.solve_dates = [...(stats.solve_dates || []), puzzleDate].slice(-60);

  saveStats(stats);
  return stats;
};

export const recordGuestFail = (puzzleDate) => {
  const stats = getStats() || defaultStats();

  if (stats.last_played_date === puzzleDate) return stats;

  stats.puzzles_played += 1;
  stats.total_guesses += 6;

  stats.current_streak = 0;

  stats.last_played_date = puzzleDate;
  saveStats(stats);
  return stats;
};
