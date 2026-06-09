import { useState } from "react";
import { Building2 } from "lucide-react";
import { useDailyPuzzle } from "@/hooks/useDailyPuzzle";
import { PuzzleHeader } from "@/components/puzzle/PuzzleHeader";
import { SilhouetteFrame } from "@/components/puzzle/SilhouetteFrame";
import { ResultBanner } from "@/components/puzzle/ResultBanner";
import { BuildingDetails } from "@/components/puzzle/BuildingDetails";
import { GuessInput } from "@/components/puzzle/GuessInput";
import { GuessGrid } from "@/components/puzzle/GuessGrid";
import { GuestStatsBar } from "@/components/puzzle/GuestStatsBar";
import { GuestSigninPrompt } from "@/components/puzzle/GuestSigninPrompt";
import { ShareCardDialog } from "@/components/puzzle/ShareCardDialog";

export default function DailyPuzzlePage() {
  const {
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
  } = useDailyPuzzle();
  const [shareOpen, setShareOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Building2 className="w-10 h-10 animate-pulse text-primary" />
      </div>
    );
  }

  if (!puzzle) return null;

  return (
    <div className="max-w-md mx-auto w-full px-4 py-6 sm:py-10 space-y-6">
      <PuzzleHeader date={puzzle.puzzle_date} guesses={puzzle.guesses} gameOver={gameOver} used={used} />

      <SilhouetteFrame silhouetteUrl={puzzle.silhouette_url} gameOver={gameOver} building={puzzle.building} />

      <ResultBanner
        gameOver={gameOver}
        isSolved={puzzle.is_solved}
        guessesUsed={puzzle.guesses_used}
        onShare={() => setShareOpen(true)}
      />

      <ShareCardDialog open={shareOpen} onOpenChange={setShareOpen} puzzle={puzzle} />

      <BuildingDetails gameOver={gameOver} building={puzzle.building} />

      {!gameOver && (
        <GuessInput
          searchQuery={searchQuery}
          searchResults={searchResults}
          submitting={submitting}
          showDropdown={showDropdown}
          setShowDropdown={setShowDropdown}
          onSearch={handleSearch}
          onGuess={handleGuess}
        />
      )}

      <GuessGrid guesses={puzzle.guesses} used={used} shakeGuess={shakeGuess} />

      {!user && guestStats.puzzles_played > 0 && <GuestStatsBar stats={guestStats} />}

      <GuestSigninPrompt show={!user && gameOver} stats={guestStats} />
    </div>
  );
}
