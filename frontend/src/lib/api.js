import axios from "axios";
import { supabase } from "@/lib/supabase";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getGuestId = () => {
  let guestId = localStorage.getItem("silhouettele_guest_id");
  if (!guestId) {
    guestId = "g_" + Math.random().toString(36).substring(2, 14) + Date.now().toString(36);
    localStorage.setItem("silhouettele_guest_id", guestId);
  }
  return guestId;
};

const api = axios.create({ baseURL: API });

// Attach Supabase JWT or guest ID to every request
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers["Authorization"] = `Bearer ${session.access_token}`;
  } else {
    config.headers["X-Guest-ID"] = getGuestId();
  }
  return config;
});

export const authAPI = {
  register: () => api.post("/auth/register"),
  getMe: () => api.get("/auth/me"),
  logout: () => api.post("/auth/logout"),
  updateProfile: (username) => api.put("/auth/profile", { username }),
};

export const puzzleAPI = {
  getToday: () => api.get("/puzzle/today"),
  submitGuess: (buildingId) => api.post("/puzzle/guess", { building_id: buildingId }),
  getCalendar: () => api.get("/puzzle/calendar"),
  getPast: (date) => api.get(`/puzzle/past/${date}`),
  getShareText: () => api.get("/puzzle/share"),
};

export const buildingAPI = {
  search: (q) => api.get(`/buildings/search?q=${encodeURIComponent(q)}`),
  list: () => api.get("/buildings"),
};

export const friendsAPI = {
  search: (q) => api.get(`/friends/search?q=${encodeURIComponent(q)}`),
  sendRequest: (friendUserId) => api.post("/friends/request", { friend_user_id: friendUserId }),
  acceptRequest: (friendUserId) => api.post("/friends/accept", { friend_user_id: friendUserId }),
  declineRequest: (friendUserId) => api.post("/friends/decline", { friend_user_id: friendUserId }),
  removeFriend: (friendUserId) => api.delete(`/friends/${friendUserId}`),
  list: () => api.get("/friends"),
  requests: () => api.get("/friends/requests"),
};

export const statsAPI = {
  getMe: () => api.get("/stats/me"),
};

export const leaderboardAPI = {
  overall: (metric) => api.get(`/leaderboard/overall?metric=${metric}`),
  friends: (metric) => api.get(`/leaderboard/friends?metric=${metric}`),
};

export const achievementsAPI = {
  getMe: () => api.get("/achievements/me"),
};

export const challengesAPI = {
  getCurrent: () => api.get("/challenges/current"),
  getLeaderboard: (type) => api.get(`/challenges/leaderboard?challenge_type=${type}`),
};

export default api;
