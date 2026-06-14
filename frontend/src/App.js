import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { Toaster } from "@/components/ui/sonner";
import { Navbar } from "@/components/Navbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import DailyPuzzlePage from "@/pages/DailyPuzzlePage";
import ProfilePage from "@/pages/ProfilePage";
import LeaderboardPage from "@/pages/LeaderboardPage";
import HistoryPage from "@/pages/HistoryPage";
import ChallengesPage from "@/pages/ChallengesPage";
import ChangelogPage from "@/pages/ChangelogPage";

function AppRouter() {
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";

  return (
    <div className="relative min-h-screen flex flex-col bg-background">
      <div className="relative z-10 flex flex-col min-h-screen">
        {!isLoginPage && <Navbar />}
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<DailyPuzzlePage />} />
            <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            <Route path="/leaderboard" element={<ProtectedRoute><LeaderboardPage /></ProtectedRoute>} />
            <Route path="/challenges" element={<ProtectedRoute><ChallengesPage /></ProtectedRoute>} />
            <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
            <Route path="/changelog" element={<ChangelogPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        {!isLoginPage && (
          <footer className="relative z-10 py-6 flex flex-col items-center gap-2">
            <p className="text-[11px] font-technical uppercase tracking-[0.25em] text-muted-foreground/60">
              A <span className="text-foreground/70 font-semibold">Loopstone Games</span> daily
            </p>
            <Link
              to="/changelog"
              data-testid="footer-changelog-link"
              className="text-[11px] font-technical uppercase tracking-[0.25em] text-muted-foreground/60 hover:text-foreground/70 transition-colors"
            >
              Changelog
            </Link>
          </footer>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
        <Toaster position="top-center" />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
