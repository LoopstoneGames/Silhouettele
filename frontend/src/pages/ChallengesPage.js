
import { useState, useEffect, useCallback } from "react";
import { challengesAPI } from "@/lib/api";
import { logError } from "@/lib/logger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CalendarDays, Swords, Trophy, Target, Flame, Star } from "lucide-react";
import { motion } from "framer-motion";

const ChallengeCard = ({ challenge }) => {
  const isWeekly = challenge.type === "weekly";
  const allComplete = challenge.goals.every((g) => g.complete);

  const goalProgress = (goal) => {
    if (typeof goal.target === "number" && goal.target > 0) {
      return Math.min(100, (goal.current / goal.target) * 100);
    }
    return goal.complete ? 100 : 0;
  };

  return (
    <Card
      className={`rounded-xl border ${allComplete ? "border-green-500/40 bg-green-500/5" : "border-border"}`}
      data-testid={`challenge-card-${challenge.type}`}
    >
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isWeekly ? (
              <Flame className="w-5 h-5 text-orange-500" />
            ) : (
              <Star className="w-5 h-5 text-yellow-500" />
            )}
            <span className="font-heading text-base">{challenge.title}</span>
          </div>
          <Badge
            variant={allComplete ? "default" : "secondary"}
            className="rounded-xl font-technical text-[10px]"
          >
            {challenge.score} PTS
          </Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground font-technical">{challenge.period}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {challenge.goals.map((goal) => (
          <div key={goal.label} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{goal.label}</span>
              <span className="font-technical font-medium">
                {goal.current}{typeof goal.target === "number" && goal.target > 0 ? `/${goal.target}` : ""}
              </span>
            </div>
            <Progress
              value={goalProgress(goal)}
              className="h-2"
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default function ChallengesPage() {
  const [challenges, setChallenges] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [lbType, setLbType] = useState("weekly");
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [challengeRes, lbRes] = await Promise.all([
        challengesAPI.getCurrent(),
        challengesAPI.getLeaderboard(lbType),
      ]);
      setChallenges(challengeRes.data);
      setLeaderboard(lbRes.data);
    } catch (err) {
      logError("Failed to load challenges:", err);
    } finally {
      setLoading(false);
    }
  }, [lbType]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Swords className="w-10 h-10 animate-pulse text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading font-extrabold text-2xl sm:text-3xl" data-testid="challenges-title">
          Challenges
        </h1>
      </div>

      {/* Challenge Progress */}
      {challenges && (
        <div className="space-y-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <ChallengeCard challenge={challenges.weekly} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <ChallengeCard challenge={challenges.monthly} />
          </motion.div>
        </div>
      )}

      {/* Challenge Leaderboard */}
      <div className="space-y-4">
        <h2 className="font-heading font-semibold text-lg" data-testid="challenge-lb-title">
          Challenge Rankings
        </h2>
        <Tabs value={lbType} onValueChange={setLbType} data-testid="challenge-tabs">
          <TabsList className="w-full rounded-xl">
            <TabsTrigger value="weekly" className="flex-1 rounded-xl text-xs uppercase tracking-wider gap-1" data-testid="challenge-tab-weekly">
              <Flame className="w-3.5 h-3.5" />
              This Week
            </TabsTrigger>
            <TabsTrigger value="monthly" className="flex-1 rounded-xl text-xs uppercase tracking-wider gap-1" data-testid="challenge-tab-monthly">
              <CalendarDays className="w-3.5 h-3.5" />
              This Month
            </TabsTrigger>
          </TabsList>

          <TabsContent value={lbType} className="mt-4">
            {leaderboard.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground text-sm">
                No participants yet. Start playing!
              </div>
            ) : (
              <div className="space-y-2">
                {leaderboard.map((entry, i) => (
                  <motion.div
                    key={entry.user_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <Card
                      className={`rounded-xl border ${
                        entry.is_me ? "border-foreground/30 bg-accent/50" : "border-border"
                      }`}
                      data-testid={`challenge-lb-row-${i}`}
                    >
                      <CardContent className="p-3 flex items-center gap-3">
                        <span className={`font-technical text-sm w-6 text-center ${
                          entry.rank <= 3 ? "font-bold text-foreground" : "text-muted-foreground"
                        }`}>
                          {entry.rank <= 3 ? ["", "1st", "2nd", "3rd"][entry.rank] : `#${entry.rank}`}
                        </span>
                        <Avatar className="h-9 w-9">
                          <AvatarImage src={entry.picture} alt={entry.name} />
                          <AvatarFallback className="text-xs">{entry.name?.charAt(0)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">
                            {entry.username || entry.name}
                            {entry.is_me && (
                              <Badge variant="outline" className="ml-2 text-[10px] rounded-xl">YOU</Badge>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {entry.solved} solved
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Trophy className="w-3.5 h-3.5 text-muted-foreground" />
                          <span className="font-technical font-medium text-sm">
                            {entry.score}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
