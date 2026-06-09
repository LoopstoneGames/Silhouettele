
import { useState, useEffect, useCallback } from "react";
import { leaderboardAPI } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Trophy, Flame, Target, Zap, ChevronDown } from "lucide-react";
import { motion } from "framer-motion";

const METRICS = [
  { key: "puzzles_solved", label: "Solved", icon: Trophy },
  { key: "current_streak", label: "Streak", icon: Flame },
  { key: "longest_streak", label: "Best Streak", icon: Zap },
  { key: "perfect_solves", label: "Perfect", icon: Target },
];

export default function LeaderboardPage() {
  const [tab, setTab] = useState("overall");
  const [metric, setMetric] = useState("puzzles_solved");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadLeaderboard = useCallback(async () => {
    setLoading(true);
    try {
      const fn = tab === "overall" ? leaderboardAPI.overall : leaderboardAPI.friends;
      const res = await fn(metric);
      setData(res.data);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [tab, metric]);

  useEffect(() => {
    loadLeaderboard();
  }, [loadLeaderboard]);

  const currentMetric = METRICS.find((m) => m.key === metric);
  const MetricIcon = currentMetric?.icon || Trophy;

  const getMetricValue = (entry) => {
    switch (metric) {
      case "puzzles_solved": return entry.puzzles_solved;
      case "current_streak": return entry.current_streak;
      case "longest_streak": return entry.longest_streak;
      case "perfect_solves": return entry.perfect_solves;
      default: return entry.puzzles_solved;
    }
  };

  return (
    <div className="max-w-lg mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading font-extrabold text-2xl sm:text-3xl" data-testid="leaderboard-title">
          Leaderboard
        </h1>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5 text-xs" data-testid="metric-selector">
              <MetricIcon className="w-3.5 h-3.5" />
              {currentMetric?.label}
              <ChevronDown className="w-3 h-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {METRICS.map(({ key, label, icon: Icon }) => (
              <DropdownMenuItem
                key={key}
                onClick={() => setMetric(key)}
                data-testid={`metric-option-${key}`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Tabs value={tab} onValueChange={setTab} data-testid="leaderboard-tabs">
        <TabsList className="w-full rounded-xl">
          <TabsTrigger value="overall" className="flex-1 rounded-xl text-xs uppercase tracking-wider" data-testid="tab-overall">
            Overall
          </TabsTrigger>
          <TabsTrigger value="friends" className="flex-1 rounded-xl text-xs uppercase tracking-wider" data-testid="tab-friends">
            Friends
          </TabsTrigger>
        </TabsList>

        <TabsContent value={tab} className="mt-4">
          {loading ? (
            <div className="py-12 text-center">
              <Trophy className="w-8 h-8 mx-auto animate-pulse text-muted-foreground" />
            </div>
          ) : data.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground text-sm">
              {tab === "friends" ? "Add friends to see their rankings!" : "No data yet. Start playing!"}
            </div>
          ) : (
            <div className="space-y-2">
              {data.map((entry, i) => (
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
                    data-testid={`leaderboard-row-${i}`}
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
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MetricIcon className="w-3.5 h-3.5 text-muted-foreground" />
                        <span className="font-technical font-medium text-sm">
                          {getMetricValue(entry)}
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
  );
}
