import { useRef, useState, useEffect } from "react";
import { toPng } from "html-to-image";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { puzzleAPI } from "@/lib/api";
import { guessEmoji } from "@/lib/directions";
import { logError } from "@/lib/logger";
import { toast } from "sonner";
import { Share2, Download, Copy, Loader2, MapPin } from "lucide-react";

const scoreLabel = (puzzle) =>
  puzzle.is_solved ? `${puzzle.guesses_used}/6` : "X/6";

export const ShareCardDialog = ({ open, onOpenChange, puzzle }) => {
  const cardRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [shareText, setShareText] = useState("");
  const guesses = puzzle.guesses || [];

  useEffect(() => {
    if (!open) return;
    puzzleAPI
      .getShareText()
      .then((res) => setShareText(res.data.share_text))
      .catch((err) => logError("Failed to load share text:", err));
  }, [open]);

  const buildPng = async () => {
    return toPng(cardRef.current, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: "#0b0b14",
    });
  };

  const handleShareImage = async () => {
    setBusy(true);
    try {
      const dataUrl = await buildPng();
      const blob = await (await fetch(dataUrl)).blob();
      const file = new File([blob], "silhouettele.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], text: shareText });
      } else {
        const a = document.createElement("a");
        a.href = dataUrl;
        a.download = "silhouettele.png";
        a.click();
        toast.success("Card downloaded!");
      }
    } catch (err) {
      if (err?.name !== "AbortError") {
        logError("Share image failed:", err);
        toast.error("Couldn't generate the card");
      }
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async () => {
    setBusy(true);
    try {
      const dataUrl = await buildPng();
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `silhouettele-${puzzle.puzzle_date}.png`;
      a.click();
      toast.success("Card downloaded!");
    } catch (err) {
      logError("Download failed:", err);
      toast.error("Couldn't generate the card");
    } finally {
      setBusy(false);
    }
  };

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      toast.success("Results copied to clipboard!");
    } catch (err) {
      logError("Copy failed:", err);
      toast.error("Couldn't copy results");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm" data-testid="share-card-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Share your result</DialogTitle>
        </DialogHeader>

        {/* The exportable card */}
        <div
          ref={cardRef}
          data-testid="share-card"
          className="rounded-2xl overflow-hidden"
          style={{
            background: "linear-gradient(160deg, #14142b 0%, #0b0b14 60%, #0b0b14 100%)",
            color: "#ffffff",
          }}
        >
          <div className="px-6 pt-6 pb-5 space-y-4">
            {/* Brand */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className="grid place-items-center h-7 w-7 rounded-lg text-sm font-black"
                  style={{ background: "#6366f1", color: "#fff" }}
                >
                  S
                </span>
                <div className="leading-none">
                  <p className="font-heading font-extrabold text-base">Silhouettele</p>
                  <p className="text-[9px] uppercase tracking-[0.25em]" style={{ color: "#9aa0b5" }}>
                    Loopstone Games
                  </p>
                </div>
              </div>
              <span
                className="font-technical text-sm font-bold px-2.5 py-1 rounded-lg"
                style={{ background: puzzle.is_solved ? "rgba(16,185,129,0.18)" : "rgba(244,63,94,0.18)", color: puzzle.is_solved ? "#34d399" : "#fb7185" }}
                data-testid="share-card-score"
              >
                {scoreLabel(puzzle)}
              </span>
            </div>

            {/* Silhouette */}
            <div className="rounded-xl p-4 flex items-center justify-center" style={{ background: "#ffffff" }}>
              {puzzle.silhouette_url && (
                <img
                  src={`${puzzle.silhouette_url}${puzzle.silhouette_url.includes("?") ? "&" : "?"}share=1`}
                  alt="silhouette"
                  crossOrigin="anonymous"
                  className="h-32 object-contain"
                />
              )}
            </div>

            {/* Building name */}
            {puzzle.building && (
              <div className="text-center">
                <p className="font-heading font-bold text-lg">{puzzle.building.name}</p>
                <p className="flex items-center justify-center gap-1 text-xs" style={{ color: "#9aa0b5" }}>
                  <MapPin className="w-3 h-3" />
                  {puzzle.building.city}, {puzzle.building.country}
                </p>
              </div>
            )}

            {/* Emoji guess grid */}
            <div className="flex items-center justify-center gap-1.5 text-2xl" data-testid="share-card-grid">
              {guesses.map((g) => (
                <span key={`scg-${g.guess_number}`}>{guessEmoji(g)}</span>
              ))}
            </div>

            <p className="text-center font-technical text-[10px] uppercase tracking-[0.3em]" style={{ color: "#6b7090" }}>
              silhouettele.cc
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-3 gap-2 pt-1">
          <Button onClick={handleShareImage} disabled={busy} className="rounded-xl gap-1.5" data-testid="share-card-share-btn">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
            Share
          </Button>
          <Button onClick={handleDownload} disabled={busy} variant="secondary" className="rounded-xl gap-1.5" data-testid="share-card-download-btn">
            <Download className="w-4 h-4" />
            Save
          </Button>
          <Button onClick={handleCopyText} variant="secondary" className="rounded-xl gap-1.5" data-testid="share-card-copy-btn">
            <Copy className="w-4 h-4" />
            Copy
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
