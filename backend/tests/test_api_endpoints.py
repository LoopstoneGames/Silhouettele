"""
Silhouettele API Tests - Backend Refactoring Verification
Tests all API endpoints after the backend was refactored from monolithic server.py to modular structure.

Modules tested:
- /api/puzzle/* - Puzzle endpoints (today, guess, share)
- /api/buildings/* - Building search and list endpoints
- /api/auth/* - Authentication endpoints (me, logout)
- /api/stats/* - Stats endpoints (requires auth)
- /api/leaderboard/* - Leaderboard endpoints (requires auth)
- /api/friends/* - Friends endpoints (requires auth)
- /api/achievements/* - Achievements endpoints (requires auth)
- /api/challenges/* - Challenges endpoints (requires auth)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPuzzleEndpoints:
    """Tests for /api/puzzle/* endpoints"""
    
    def test_get_today_puzzle_with_guest_id(self):
        """GET /api/puzzle/today - Returns puzzle for guest users with X-Guest-ID header"""
        guest_id = f"pytest-guest-{uuid.uuid4().hex[:8]}"
        response = requests.get(
            f"{BASE_URL}/api/puzzle/today",
            headers={"X-Guest-ID": guest_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify response structure
        assert "puzzle_date" in data
        assert "guesses_used" in data
        assert "guesses_remaining" in data
        assert "is_solved" in data
        assert "is_failed" in data
        assert "guesses" in data
        assert "silhouette_url" in data
        assert "is_guest" in data
        
        # Verify values for fresh guest
        assert data["is_guest"] == True
        assert data["guesses_used"] == 0
        assert data["guesses_remaining"] == 6
        assert data["is_solved"] == False
        assert data["is_failed"] == False
        assert len(data["guesses"]) == 0
        assert data["silhouette_url"].startswith("https://")
    
    def test_get_today_puzzle_without_guest_id_returns_401(self):
        """GET /api/puzzle/today - Returns 401 without X-Guest-ID header"""
        response = requests.get(f"{BASE_URL}/api/puzzle/today")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_submit_guess_for_guest_user(self):
        """POST /api/puzzle/guess - Submits a guess for guest users"""
        guest_id = f"pytest-guess-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers={"X-Guest-ID": guest_id, "Content-Type": "application/json"},
            json={"building_id": "b003"}  # Colosseum
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "guess" in data
        assert "guesses_used" in data
        assert "guesses_remaining" in data
        assert "is_solved" in data
        assert "is_failed" in data
        assert "guesses" in data
        
        # Verify guess data
        guess = data["guess"]
        assert guess["guess_building_id"] == "b003"
        assert guess["guess_building_name"] == "Colosseum"
        assert guess["guess_number"] == 1
        assert "is_correct" in guess
        assert "direction" in guess or guess["is_correct"]
        assert "direction_arrow" in guess or guess["is_correct"]
        assert "distance_km" in guess or guess["is_correct"]
    
    def test_submit_duplicate_guess_returns_400(self):
        """POST /api/puzzle/guess - Returns 400 for duplicate guess"""
        guest_id = f"pytest-dup-{uuid.uuid4().hex[:8]}"
        
        # First guess
        requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers={"X-Guest-ID": guest_id, "Content-Type": "application/json"},
            json={"building_id": "b002"}
        )
        
        # Duplicate guess
        response = requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers={"X-Guest-ID": guest_id, "Content-Type": "application/json"},
            json={"building_id": "b002"}
        )
        assert response.status_code == 400
        assert "already guessed" in response.json()["detail"].lower()
    
    def test_submit_invalid_building_id_returns_400(self):
        """POST /api/puzzle/guess - Returns 400 for invalid building_id"""
        guest_id = f"pytest-invalid-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers={"X-Guest-ID": guest_id, "Content-Type": "application/json"},
            json={"building_id": "invalid_building_123"}
        )
        assert response.status_code == 400
        assert "not in database" in response.json()["detail"].lower()
    
    def test_get_share_text_after_guess(self):
        """GET /api/puzzle/share - Returns share text after guessing"""
        guest_id = f"pytest-share-{uuid.uuid4().hex[:8]}"
        
        # Make a guess first
        requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers={"X-Guest-ID": guest_id, "Content-Type": "application/json"},
            json={"building_id": "b004"}  # Sydney Opera House
        )
        
        # Get share text
        response = requests.get(
            f"{BASE_URL}/api/puzzle/share",
            headers={"X-Guest-ID": guest_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "share_text" in data
        assert "is_solved" in data
        assert "score" in data
        assert "Silhouettele" in data["share_text"]
    
    def test_get_share_text_without_guess_returns_400(self):
        """GET /api/puzzle/share - Returns 400 when no guesses made"""
        guest_id = f"pytest-noshare-{uuid.uuid4().hex[:8]}"
        
        response = requests.get(
            f"{BASE_URL}/api/puzzle/share",
            headers={"X-Guest-ID": guest_id}
        )
        assert response.status_code == 400
        assert "no guesses" in response.json()["detail"].lower()


class TestBuildingsEndpoints:
    """Tests for /api/buildings/* endpoints"""
    
    def test_list_all_buildings(self):
        """GET /api/buildings - Returns all 60 buildings"""
        response = requests.get(
            f"{BASE_URL}/api/buildings",
            headers={"X-Guest-ID": "pytest-buildings"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 60, f"Expected 60 buildings, got {len(data)}"
        
        # Verify building structure
        building = data[0]
        assert "building_id" in building
        assert "name" in building
        assert "city" in building
        assert "country" in building
    
    def test_search_buildings_by_name(self):
        """GET /api/buildings/search?q=eiffel - Returns matching buildings"""
        response = requests.get(
            f"{BASE_URL}/api/buildings/search?q=eiffel",
            headers={"X-Guest-ID": "pytest-search"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify Eiffel Tower is in results
        names = [b["name"].lower() for b in data]
        assert any("eiffel" in name for name in names)
    
    def test_search_buildings_by_city(self):
        """GET /api/buildings/search?q=paris - Returns buildings in Paris"""
        response = requests.get(
            f"{BASE_URL}/api/buildings/search?q=paris",
            headers={"X-Guest-ID": "pytest-city"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Eiffel Tower, Notre-Dame, Arc de Triomphe, etc.
    
    def test_search_buildings_short_query_returns_empty(self):
        """GET /api/buildings/search?q=a - Returns empty for short queries"""
        response = requests.get(
            f"{BASE_URL}/api/buildings/search?q=a",
            headers={"X-Guest-ID": "pytest-short"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_search_buildings_no_match_returns_empty(self):
        """GET /api/buildings/search?q=xyznonexistent - Returns empty for no match"""
        response = requests.get(
            f"{BASE_URL}/api/buildings/search?q=xyznonexistent",
            headers={"X-Guest-ID": "pytest-nomatch"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestAuthEndpoints:
    """Tests for /api/auth/* endpoints"""
    
    def test_get_me_unauthenticated_returns_401(self):
        """GET /api/auth/me - Returns 401 for unauthenticated users"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
    
    def test_logout_works_without_session(self):
        """POST /api/auth/logout - Works without errors even without session"""
        response = requests.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["message"].lower() == "logged out"


class TestProtectedEndpoints:
    """Tests for auth-protected endpoints that should return 401 for guests"""
    
    def test_stats_me_requires_auth(self):
        """GET /api/stats/me - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/stats/me",
            headers={"X-Guest-ID": "pytest-stats"}
        )
        assert response.status_code == 401
    
    def test_puzzle_calendar_requires_auth(self):
        """GET /api/puzzle/calendar - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/puzzle/calendar",
            headers={"X-Guest-ID": "pytest-calendar"}
        )
        assert response.status_code == 401
    
    def test_puzzle_past_requires_auth(self):
        """GET /api/puzzle/past/{date} - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/puzzle/past/2026-01-01",
            headers={"X-Guest-ID": "pytest-past"}
        )
        assert response.status_code == 401
    
    def test_friends_list_requires_auth(self):
        """GET /api/friends - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/friends",
            headers={"X-Guest-ID": "pytest-friends"}
        )
        assert response.status_code == 401
    
    def test_leaderboard_overall_requires_auth(self):
        """GET /api/leaderboard/overall - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard/overall?metric=streak",
            headers={"X-Guest-ID": "pytest-leaderboard"}
        )
        assert response.status_code == 401
    
    def test_achievements_me_requires_auth(self):
        """GET /api/achievements/me - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/achievements/me",
            headers={"X-Guest-ID": "pytest-achievements"}
        )
        assert response.status_code == 401
    
    def test_challenges_current_requires_auth(self):
        """GET /api/challenges/current - Returns 401 for guests"""
        response = requests.get(
            f"{BASE_URL}/api/challenges/current",
            headers={"X-Guest-ID": "pytest-challenges"}
        )
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
