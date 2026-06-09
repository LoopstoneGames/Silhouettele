"""
Silhouettele Authenticated Endpoint Tests
Tests endpoints that require a real Supabase JWT (logged-in user).
"""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv

# Load backend .env so we can use SUPABASE_URL + SUPABASE_ANON_KEY
load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://daily-silhouette.preview.emergentagent.com").rstrip("/")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

TEST_EMAIL = os.environ.get("TEST_USER_EMAIL", "qatester1780618719@gmail.com")
TEST_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "")


@pytest.fixture(scope="module")
def access_token():
    """Login to Supabase and return access_token."""
    assert SUPABASE_URL, "SUPABASE_URL missing"
    assert SUPABASE_ANON_KEY, "SUPABASE_ANON_KEY missing"
    if not TEST_PASSWORD:
        pytest.skip("TEST_USER_PASSWORD env var not set; skipping authed tests")
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    body = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    assert r.status_code == 200, f"Supabase login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


# ------------------ AUTH ------------------
class TestAuth:
    def test_register_creates_or_returns_user(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/auth/register", headers=auth_headers)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert "user_id" in data or "id" in data
        assert data.get("email") == TEST_EMAIL

    def test_me_returns_user(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("email") == TEST_EMAIL
        assert "user_id" in data or "id" in data

    def test_me_invalid_token(self):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert r.status_code == 401


# ------------------ PUZZLE (authed) ------------------
class TestPuzzleAuthed:
    def test_puzzle_today_authed(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/puzzle/today", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("is_guest") is False
        assert "silhouette_url" in data and data["silhouette_url"].startswith("http")
        assert data["guesses_remaining"] <= 6

    def test_puzzle_calendar_authed(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/puzzle/calendar", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))


# ------------------ STATS / LEADERBOARD / ACHIEVEMENTS / CHALLENGES ------------------
class TestUserData:
    def test_stats_me(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/stats/me", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_leaderboard_overall(self, auth_headers):
        for metric in ("streak", "wins", "win_rate"):
            r = requests.get(
                f"{BASE_URL}/api/leaderboard/overall?metric={metric}",
                headers=auth_headers,
            )
            assert r.status_code == 200, f"metric={metric} -> {r.status_code} {r.text}"
            assert isinstance(r.json(), (list, dict))

    def test_leaderboard_friends(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/leaderboard/friends", headers=auth_headers)
        assert r.status_code == 200, r.text

    def test_achievements_me(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/achievements/me", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_challenges_current(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/challenges/current", headers=auth_headers)
        assert r.status_code == 200, r.text


# ------------------ FRIENDS ------------------
class TestFriends:
    def test_friends_list(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/friends", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_friend_requests(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/friends/requests", headers=auth_headers)
        assert r.status_code == 200, r.text

    def test_friend_search(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/friends/search?q=qa", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))


# ------------------ GUESS CORRECT FLOW (guest, deterministic) ------------------
class TestCorrectGuessFlow:
    """Use silhouette filename to derive today's building_id and submit a correct guess."""

    def test_correct_guess_marks_solved(self):
        guest_id = f"correct_{uuid.uuid4().hex[:10]}"
        headers = {"X-Guest-ID": guest_id, "Content-Type": "application/json"}

        r = requests.get(f"{BASE_URL}/api/puzzle/today", headers=headers)
        assert r.status_code == 200, r.text
        puzzle = r.json()
        url = puzzle["silhouette_url"]
        # Extract building_id from filename, e.g. b028.png
        fname = url.rsplit("/", 1)[-1].split("?")[0]
        building_id = fname.rsplit(".", 1)[0]
        assert building_id.startswith("b"), f"Unexpected silhouette filename: {fname}"

        # Submit correct guess
        gr = requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers=headers,
            json={"building_id": building_id},
        )
        assert gr.status_code == 200, gr.text
        data = gr.json()
        assert data["is_solved"] is True, data
        assert data["guess"]["is_correct"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
