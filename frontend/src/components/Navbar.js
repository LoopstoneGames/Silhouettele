import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Building2, Sun, Moon, Trophy, CalendarDays, User, LogOut, Swords, LogIn } from "lucide-react";

export const Navbar = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const navLinks = user
    ? [
        { path: "/", label: "Play", icon: Building2 },
        { path: "/leaderboard", label: "Ranks", icon: Trophy },
        { path: "/challenges", label: "Challenges", icon: Swords },
        { path: "/history", label: "History", icon: CalendarDays },
      ]
    : [{ path: "/", label: "Play", icon: Building2 }];

  return (
    <header
      data-testid="main-navbar"
      className="h-16 sticky top-0 z-50 flex items-center justify-between px-4 sm:px-6 border-b border-border/60 bg-background/70 backdrop-blur-xl"
    >
      <div className="flex items-center gap-3 sm:gap-5">
        <Link to="/" className="flex items-center gap-2.5 group shrink-0" data-testid="nav-logo">
          <span className="grid place-items-center h-9 w-9 rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/30 group-hover:scale-105 transition-transform">
            <Building2 className="w-5 h-5" strokeWidth={2.5} />
          </span>
          <span className="hidden sm:flex flex-col leading-none">
            <span className="font-heading font-black text-base tracking-tight">Silhouettele</span>
            <span className="font-technical text-[8px] uppercase tracking-[0.3em] text-muted-foreground">Loopstone Games</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 bg-muted/50 rounded-full p-1">
          {navLinks.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path;
            return (
              <Link key={path} to={path} data-testid={`nav-link-${label.toLowerCase()}`}>
                <span
                  className={`flex items-center gap-1.5 rounded-full px-2.5 sm:px-3.5 py-1.5 text-xs font-semibold tracking-tight transition-colors ${
                    active
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{label}</span>
                </span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="rounded-full"
          data-testid="theme-toggle-btn"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>

        {user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild data-testid="user-menu-trigger">
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8 ring-2 ring-border">
                  <AvatarImage src={user.picture} alt={user.name} />
                  <AvatarFallback className="text-xs font-semibold bg-primary/10 text-primary">
                    {user.name?.charAt(0)?.toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 rounded-xl">
              <DropdownMenuItem onClick={() => navigate("/profile")} data-testid="nav-profile-link" className="rounded-lg">
                <User className="w-4 h-4 mr-2" /> Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} data-testid="nav-logout-btn" className="rounded-lg">
                <LogOut className="w-4 h-4 mr-2" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button
            size="sm"
            onClick={() => navigate("/login")}
            className="rounded-full gap-1.5 text-xs font-semibold px-4"
            data-testid="nav-signin-btn"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign In</span>
          </Button>
        )}
      </div>
    </header>
  );
};
