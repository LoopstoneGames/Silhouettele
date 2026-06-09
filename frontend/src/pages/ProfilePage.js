
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { statsAPI, friendsAPI, achievementsAPI } from "@/lib/api";
import { authAPI } from "@/lib/api";
import { logError } from "@/lib/logger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  User, Users, UserPlus, UserCheck, UserX, Search, Trophy,
  Flame, Target, Zap, Hash, Check, X, Edit3, Save,
  Award, Crown, Rocket, Star, Crosshair, Globe, Building2,
} from "lucide-react";
import { motion } from "framer-motion";

export default function ProfilePage() {
  const { user, login } = useAuth();
  const [stats, setStats] = useState(null);
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [editingUsername, setEditingUsername] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [achievements, setAchievements] = useState(null);

  const ICON_MAP = {
    "award": Award, "flame": Flame, "building-2": Building2, "crown": Crown,
    "zap": Zap, "rocket": Rocket, "star": Star, "target": Target,
    "crosshair": Crosshair, "globe": Globe,
  };

  const loadData = useCallback(async () => {
    try {
      const [statsRes, friendsRes, requestsRes, achRes] = await Promise.all([
        statsAPI.getMe(),
        friendsAPI.list(),
        friendsAPI.requests(),
        achievementsAPI.getMe(),
      ]);
      setStats(statsRes.data);
      setFriends(friendsRes.data);
      setRequests(requestsRes.data);
      setAchievements(achRes.data);
      // Toast for new badges
      const newBadges = achRes.data?.achievements?.filter((a) => a.is_new && a.earned);
      if (newBadges?.length > 0) {
        newBadges.forEach((b) => {
          toast.success(`Badge Unlocked: ${b.name}!`, { description: b.description });
        });
      }
    } catch (err) {
      logError("Failed to load profile data:", err);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearchUsers = async () => {
    if (searchQuery.length < 2) return;
    try {
      const res = await friendsAPI.search(searchQuery);
      setSearchResults(res.data);
    } catch {
      toast.error("Search failed");
    }
  };

  const handleSendRequest = async (friendId) => {
    try {
      await friendsAPI.sendRequest(friendId);
      toast.success("Friend request sent!");
      setSearchResults((prev) => prev.filter((u) => u.user_id !== friendId));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send request");
    }
  };

  const handleAcceptRequest = async (friendId) => {
    try {
      await friendsAPI.acceptRequest(friendId);
      toast.success("Friend request accepted!");
      loadData();
    } catch {
      toast.error("Failed to accept request");
    }
  };

  const handleDeclineRequest = async (friendId) => {
    try {
      await friendsAPI.declineRequest(friendId);
      setRequests((prev) => prev.filter((r) => r.user_id !== friendId));
    } catch {
      toast.error("Failed to decline request");
    }
  };

  const handleUpdateUsername = async () => {
    try {
      const res = await authAPI.updateProfile(newUsername);
      login(res.data);
      setEditingUsername(false);
      toast.success("Username updated!");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update username");
    }
  };

  const statItems = stats
    ? [
        { label: "Played", value: stats.puzzles_played, icon: Hash },
        { label: "Solved", value: stats.puzzles_solved, icon: Trophy },
        { label: "Streak", value: stats.current_streak, icon: Flame },
        { label: "Best", value: stats.longest_streak, icon: Zap },
        { label: "Avg", value: stats.avg_guesses, icon: Target },
        { label: "Perfect", value: stats.perfect_solves, icon: Check },
      ]
    : [];

  return (
    <div className="max-w-lg mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-6 sm:space-y-8">
      {/* Profile Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-4"
      >
        <Avatar className="h-16 w-16 ring-2 ring-primary/20" data-testid="profile-avatar">
          <AvatarImage src={user?.picture} alt={user?.name} />
          <AvatarFallback className="text-lg font-heading font-bold">
            {user?.name?.charAt(0)?.toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <h1 className="font-heading font-extrabold text-2xl" data-testid="profile-name">
            {user?.name}
          </h1>
          <div className="flex items-center gap-2">
            {editingUsername ? (
              <div className="flex items-center gap-2 mt-1">
                <Input
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="h-8 w-40 rounded-xl text-sm"
                  placeholder="username"
                  data-testid="username-input"
                />
                <Button size="icon" variant="ghost" onClick={handleUpdateUsername} className="h-8 w-8" data-testid="save-username-btn">
                  <Save className="w-3.5 h-3.5" />
                </Button>
                <Button size="icon" variant="ghost" onClick={() => setEditingUsername(false)} className="h-8 w-8">
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            ) : (
              <button
                className="flex items-center gap-1.5 text-muted-foreground text-sm hover:text-foreground transition-colors"
                onClick={() => { setNewUsername(user?.username || ""); setEditingUsername(true); }}
                data-testid="edit-username-btn"
              >
                @{user?.username || "set username"}
                <Edit3 className="w-3 h-3" />
              </button>
            )}
          </div>
          <p className="text-xs text-muted-foreground font-technical mt-1">
            Joined {user?.join_date ? new Date(user.join_date).toLocaleDateString() : "recently"}
          </p>
        </div>
      </motion.div>

      {/* Stats Grid */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="grid grid-cols-3 gap-3" data-testid="stats-grid">
            {statItems.map(({ label, value, icon: Icon }) => (
              <div key={label} className="bento bento-lift p-4 text-center">
                <Icon className="w-4 h-4 mx-auto text-primary mb-1.5" />
                <p className="font-heading font-black text-2xl tabular-nums">{value}</p>
                <p className="text-[10px] text-muted-foreground font-technical uppercase tracking-[0.15em] mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Achievements */}
      {achievements && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-3"
        >
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-semibold text-base">
              Badges
            </h2>
            <span className="text-xs text-muted-foreground font-technical">
              {achievements.earned_count}/{achievements.total_count}
            </span>
          </div>
          <div className="grid grid-cols-5 gap-2" data-testid="achievements-grid">
            {achievements.achievements.map((a) => {
              const IconComp = ICON_MAP[a.icon] || Award;
              return (
                <div
                  key={a.id}
                  className={`flex flex-col items-center gap-1 p-2 rounded-xl border transition-all ${
                    a.earned
                      ? "border-foreground/20 bg-accent/50"
                      : "border-border/50 opacity-30"
                  } ${a.is_new ? "animate-pulse-glow" : ""}`}
                  title={`${a.name}: ${a.description}`}
                  data-testid={`badge-${a.id}`}
                >
                  <IconComp className={`w-5 h-5 ${a.earned ? "text-foreground" : "text-muted-foreground"}`} />
                  <span className="text-[9px] font-technical text-center leading-tight truncate w-full">
                    {a.name}
                  </span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Friends Tabs */}
      <Tabs defaultValue="friends" data-testid="profile-tabs">
        <TabsList className="w-full rounded-xl">
          <TabsTrigger value="friends" className="flex-1 rounded-xl text-xs uppercase tracking-wider gap-1">
            <Users className="w-3.5 h-3.5" />
            Friends ({friends.length})
          </TabsTrigger>
          <TabsTrigger value="requests" className="flex-1 rounded-xl text-xs uppercase tracking-wider gap-1">
            <UserPlus className="w-3.5 h-3.5" />
            Requests ({requests.length})
          </TabsTrigger>
          <TabsTrigger value="add" className="flex-1 rounded-xl text-xs uppercase tracking-wider gap-1">
            <Search className="w-3.5 h-3.5" />
            Add
          </TabsTrigger>
        </TabsList>

        <TabsContent value="friends" className="space-y-2 mt-4">
          {friends.length === 0 ? (
            <p className="text-center text-muted-foreground text-sm py-8">No friends yet. Add some!</p>
          ) : (
            friends.map((f) => (
              <Card key={f.user_id} className="rounded-xl border border-border" data-testid={`friend-${f.user_id}`}>
                <CardContent className="p-3 flex items-center gap-3">
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={f.picture} alt={f.name} />
                    <AvatarFallback className="text-xs">{f.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{f.name}</p>
                    <p className="text-xs text-muted-foreground">@{f.username}</p>
                  </div>
                  <UserCheck className="w-4 h-4 text-green-500" />
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="requests" className="space-y-2 mt-4">
          {requests.length === 0 ? (
            <p className="text-center text-muted-foreground text-sm py-8">No pending requests</p>
          ) : (
            requests.map((r) => (
              <Card key={r.user_id} className="rounded-xl border border-border" data-testid={`request-${r.user_id}`}>
                <CardContent className="p-3 flex items-center gap-3">
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={r.picture} alt={r.name} />
                    <AvatarFallback className="text-xs">{r.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{r.name}</p>
                    <p className="text-xs text-muted-foreground">@{r.username}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-green-500 hover:bg-green-500/10"
                      onClick={() => handleAcceptRequest(r.user_id)}
                      data-testid={`accept-request-${r.user_id}`}
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-red-500 hover:bg-red-500/10"
                      onClick={() => handleDeclineRequest(r.user_id)}
                      data-testid={`decline-request-${r.user_id}`}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="add" className="space-y-3 mt-4">
          <div className="flex gap-2">
            <Input
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearchUsers()}
              className="rounded-xl"
              data-testid="search-users-input"
            />
            <Button
              onClick={handleSearchUsers}
              variant="secondary"
              className="rounded-xl"
              data-testid="search-users-btn"
            >
              <Search className="w-4 h-4" />
            </Button>
          </div>
          <div className="space-y-2">
            {searchResults.map((u) => (
              <Card key={u.user_id} className="rounded-xl border border-border" data-testid={`search-result-${u.user_id}`}>
                <CardContent className="p-3 flex items-center gap-3">
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={u.picture} alt={u.name} />
                    <AvatarFallback className="text-xs">{u.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{u.name}</p>
                    <p className="text-xs text-muted-foreground">@{u.username}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="rounded-xl text-xs gap-1"
                    onClick={() => handleSendRequest(u.user_id)}
                    data-testid={`add-friend-${u.user_id}`}
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    Add
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
