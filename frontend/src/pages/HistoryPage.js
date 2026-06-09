import { useState, useEffect, useCallback } from "react";
import { puzzleAPI } from "@/lib/api";
import { logError } from "@/lib/logger";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { guessEmoji } from "@/lib/directions";
import { CalendarDays, X, ArrowLeft, MapPin, Building2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function HistoryPage() {
  const [calendarData, setCalendarData] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [pastPuzzle, setPastPuzzle] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await puzzleAPI.getCalendar();
        setCalendarData(res.data);
      } catch (err) {
        logError("Failed to load puzzle calendar:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const loadPastPuzzle = useCallback(async (dateStr) => {
    try {
      const res = await puzzleAPI.getPast(dateStr);
      setPastPuzzle(res.data);
    } catch {
      setPastPuzzle(null);
    }
  }, []);

  const handleSelectDate = (date) => {
    if (!date) return;
    const dateStr = [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
    setSelectedDate(dateStr);
    loadPastPuzzle(dateStr);
  };

  const solvedDates = calendarData.filter((d) => d.solved).map((d) => new Date(d.date + "T00:00:00"));
  const attemptedDates = calendarData.filter((d) => d.attempted && !d.solved).map((d) => new Date(d.date + "T00:00:00"));

  const modifiers = {
    solved: solvedDates,
    attempted: attemptedDates,
  };

  const modifiersStyles = {
    solved: { backgroundColor: "hsl(var(--success) / 0.2)", color: "hsl(var(--success))", fontWeight: 700 },
    attempted: { backgroundColor: "hsl(var(--destructive) / 0.15)", color: "hsl(var(--destructive))", fontWeight: 600 },
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <CalendarDays className="w-10 h-10 animate-pulse text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-4 sm:space-y-6">
      <h1 className="font-heading font-extrabold text-2xl sm:text-3xl" data-testid="history-title">
        Past Puzzles
      </h1>

      <AnimatePresence mode="wait">
        {!selectedDate ? (
          <motion.div
            key="calendar"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Card className="rounded-xl border border-border" data-testid="history-calendar">
              <CardContent className="p-4 flex justify-center">
                <Calendar
                  mode="single"
                  onSelect={handleSelectDate}
                  modifiers={modifiers}
                  modifiersStyles={modifiersStyles}
                  disabled={{ after: new Date() }}
                  className="rounded-xl"
                />
              </CardContent>
            </Card>
            <div className="flex items-center justify-center gap-6 mt-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-xl bg-green-500/20 border border-green-500/30" />
                Solved
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-xl bg-red-500/15 border border-red-500/20" />
                Attempted
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-4"
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setSelectedDate(null); setPastPuzzle(null); }}
              className="rounded-xl gap-1.5 text-xs"
              data-testid="back-to-calendar"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Calendar
            </Button>

            <Card className="rounded-xl border border-border" data-testid="past-puzzle-card">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between">
                  <span className="font-heading text-lg">{selectedDate}</span>
                  {pastPuzzle?.is_solved && (
                    <Badge className="bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30 rounded-xl">
                      Solved
                    </Badge>
                  )}
                  {pastPuzzle?.is_failed && (
                    <Badge variant="destructive" className="rounded-xl">Failed</Badge>
                  )}
                  {pastPuzzle && !pastPuzzle.is_solved && !pastPuzzle.is_failed && pastPuzzle.guesses_used === 0 && (
                    <Badge variant="secondary" className="rounded-xl">Not Played</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {pastPuzzle?.building && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-foreground/60" />
                      <h3 className="font-heading font-bold text-lg">{pastPuzzle.building.name}</h3>
                    </div>
                    <div className="flex items-center gap-1.5 text-muted-foreground text-sm">
                      <MapPin className="w-3.5 h-3.5" />
                      {pastPuzzle.building.city}, {pastPuzzle.building.country}
                    </div>
                    {pastPuzzle.building.fun_fact && (
                      <p className="text-sm text-foreground/70 mt-2">{pastPuzzle.building.fun_fact}</p>
                    )}
                  </div>
                )}

                {pastPuzzle?.guesses?.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground font-technical uppercase">Your Guesses</p>
                    {pastPuzzle.guesses.map((g, i) => (
                      <div
                        key={`past-guess-${g.guess_number}`}
                        className={`flex items-center justify-between p-2.5 rounded-xl border ${
                          g.is_correct ? "border-green-500/30 bg-green-500/5" : "border-border"
                        }`}
                        data-testid={`past-guess-${i}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-technical text-xs text-muted-foreground w-4">{g.guess_number}</span>
                          <span className="text-sm font-medium">{g.guess_building_name}</span>
                        </div>
                        {g.is_correct ? (
                          <span className="text-base">{guessEmoji(g)}</span>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <span className="text-base">{guessEmoji(g)}</span>
                            <span className="font-technical text-xs text-muted-foreground">
                              {g.distance_km?.toLocaleString()} km
                            </span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
