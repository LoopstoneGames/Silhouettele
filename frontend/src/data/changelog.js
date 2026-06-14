// Player-facing changelog.
// Add a new entry to the TOP of this list each time a game-related change ships.
// Keep the tone friendly and short — players, not engineers, read this.
//
// { date: "YYYY-MM-DD", title: "...", body: ["paragraph one", "paragraph two", ...] }

export const CHANGELOG = [
  {
    date: "2026-06-14",
    title: "Changelog",
    body: [
      "You can now follow along with every update we make to the game right here.",
      "Each time we ship something new, we'll leave a friendly note so you always know what's changed.",
      "Thanks for playing!",
      "— Loopstone Games",
    ],
  },
  {
    date: "2026-06-09",
    title: "A Fresh New Look",
    body: [
      "Silhouettele has a brand new logo and a cleaner, calmer board to make your daily guess feel just right.",
      "Same puzzle you love, a little nicer to look at.",
      "— Loopstone Games",
    ],
  },
  {
    date: "2026-06-09",
    title: "Past Puzzles",
    body: [
      "Missed a day? You can now browse the calendar and revisit any past puzzle to see the building and how you did.",
      "Head to the History tab to take a look.",
      "Thanks for playing!",
      "— Loopstone Games",
    ],
  },
  {
    date: "2026-06-09",
    title: "Challenge a Friend",
    body: [
      "You can now challenge your friends to a head-to-head and see who knows their skylines best. 🏙️",
      "Find it in the Challenges tab.",
      "— Loopstone Games",
    ],
  },
  {
    date: "2026-06-09",
    title: "Leaderboards & Ranks",
    body: [
      "Climb the ranks! We've added daily and all-time leaderboards so you can see how you stack up against players around the world.",
      "Thank you all for playing!",
      "— Loopstone Games",
    ],
  },
  {
    date: "2026-06-09",
    title: "Welcome to Silhouettele",
    body: [
      "A new daily puzzle is here. Every day you get six guesses to name a famous building from its silhouette — wrong guesses point you in the right direction.",
      "Come back each day for a fresh one. Good luck!",
      "— Loopstone Games",
    ],
  },
];

const ORDINAL = (n) => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// "2026-06-04" -> "June 4th, 2026"
export const formatChangelogDate = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${ORDINAL(d)}, ${y}`;
};
