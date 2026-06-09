// Maps a 16-point compass code (N, NNE, ... ) to a consistent emoji glyph.
// Using emoji-presentation glyphs (with U+FE0F) so all 8 directions render
// uniformly across platforms (iOS was rendering diagonals as colour emoji
// and cardinals as thin text arrows).
const COMPASS_EMOJI = {
  N: "\u2B06\uFE0F",
  NNE: "\u2197\uFE0F", NE: "\u2197\uFE0F", ENE: "\u2197\uFE0F",
  E: "\u27A1\uFE0F",
  ESE: "\u2198\uFE0F", SE: "\u2198\uFE0F", SSE: "\u2198\uFE0F",
  S: "\u2B07\uFE0F",
  SSW: "\u2199\uFE0F", SW: "\u2199\uFE0F", WSW: "\u2199\uFE0F",
  W: "\u2B05\uFE0F",
  WNW: "\u2196\uFE0F", NW: "\u2196\uFE0F", NNW: "\u2196\uFE0F",
};

const TARGET_EMOJI = "\uD83C\uDFAF"; // 🎯

// Returns the emoji to show for a guess row.
export function guessEmoji(guess) {
  if (guess.is_correct) return TARGET_EMOJI;
  return COMPASS_EMOJI[guess.direction] || "";
}
