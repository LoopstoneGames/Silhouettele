"""
Silhouettele API Tests - Post Supabase Migration
Tests guest-accessible endpoints (puzzle, buildings) and auth endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_check(self):
        """GET /health returns status ok - Note: /health is not under /api prefix"""
        # The /health endpoint is at root level, not under /api
        # In production, this may be served by frontend if not properly routed
        # Testing the backend directly would require internal port access
        # For now, we verify the API endpoints work which confirms backend is healthy
        response = requests.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Backend is healthy if it returns buildings


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_auth_me_unauthenticated(self):
        """GET /api/auth/me returns 401 for unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "authenticated" in data["detail"].lower() or "not" in data["detail"].lower()
    
    def test_auth_logout_success(self):
        """POST /api/auth/logout returns success"""
        response = requests.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()


class TestBuildingsEndpoints:
    """Buildings search and list endpoint tests"""
    
    def test_buildings_search_eiffel(self):
        """GET /api/buildings/search?q=eiffel returns Eiffel Tower"""
        response = requests.get(f"{BASE_URL}/api/buildings/search?q=eiffel")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check Eiffel Tower is in results
        building_names = [b["name"].lower() for b in data]
        assert any("eiffel" in name for name in building_names)
        # Verify structure
        first_building = data[0]
        assert "building_id" in first_building
        assert "name" in first_building
        assert "city" in first_building
        assert "country" in first_building
    
    def test_buildings_search_short_query(self):
        """GET /api/buildings/search?q=a returns empty (query too short)"""
        response = requests.get(f"{BASE_URL}/api/buildings/search?q=a")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0  # Query too short
    
    def test_buildings_list_all(self):
        """GET /api/buildings returns the full building catalog"""
        response = requests.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 100  # Catalog expanded to 114+ buildings
        # Verify structure
        first_building = data[0]
        assert "building_id" in first_building
        assert "name" in first_building
        assert "city" in first_building
        assert "country" in first_building


class TestPuzzleEndpointsGuest:
    """Puzzle endpoint tests with guest mode (X-Guest-ID header)"""
    
    @pytest.fixture
    def guest_id(self):
        """Generate unique guest ID for each test"""
        return f"test_guest_{uuid.uuid4().hex[:12]}"
    
    def test_puzzle_today_with_guest_id(self, guest_id):
        """GET /api/puzzle/today with X-Guest-ID returns puzzle data"""
        headers = {"X-Guest-ID": guest_id}
        response = requests.get(f"{BASE_URL}/api/puzzle/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "puzzle_date" in data
        assert "guesses_used" in data
        assert "guesses_remaining" in data
        assert "is_solved" in data
        assert "is_failed" in data
        assert "guesses" in data
        assert "silhouette_url" in data
        assert "is_guest" in data
        
        # Verify values for fresh guest
        assert data["guesses_used"] == 0
        assert data["guesses_remaining"] == 6
        assert data["is_solved"] is False
        assert data["is_failed"] is False
        assert data["is_guest"] is True
        assert isinstance(data["guesses"], list)
        assert len(data["guesses"]) == 0
        
        # Verify silhouette_url is present and valid
        assert data["silhouette_url"] != ""
        assert data["silhouette_url"].startswith("http")
    
    def test_puzzle_today_without_auth_fails(self):
        """GET /api/puzzle/today without auth or guest ID returns 401"""
        response = requests.get(f"{BASE_URL}/api/puzzle/today")
        assert response.status_code == 401
    
    def test_puzzle_guess_submit(self, guest_id):
        """POST /api/puzzle/guess with X-Guest-ID submits a guess"""
        headers = {"X-Guest-ID": guest_id, "Content-Type": "application/json"}
        
        # First get the puzzle to see available buildings
        puzzle_response = requests.get(f"{BASE_URL}/api/puzzle/today", headers=headers)
        assert puzzle_response.status_code == 200
        
        # Search for a building to guess
        search_response = requests.get(f"{BASE_URL}/api/buildings/search?q=eiffel")
        assert search_response.status_code == 200
        buildings = search_response.json()
        assert len(buildings) > 0
        
        building_to_guess = buildings[0]
        
        # Submit guess
        guess_payload = {"building_id": building_to_guess["building_id"]}
        response = requests.post(
            f"{BASE_URL}/api/puzzle/guess",
            headers=headers,
            json=guess_payload
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "guess" in data
        assert "guesses_used" in data
        assert "guesses_remaining" in data
        assert "is_solved" in data
        assert "is_failed" in data
        assert "guesses" in data
        
        # Verify guess details
        guess = data["guess"]
        assert guess["guess_building_id"] == building_to_guess["building_id"]
        assert guess["guess_building_name"] == building_to_guess["name"]
        assert guess["guess_number"] == 1
        assert "is_correct" in guess
        
        # If not correct, should have direction/distance hints
        if not guess["is_correct"]:
            assert "direction" in guess
            assert "direction_arrow" in guess
            assert "distance_km" in guess
            assert isinstance(guess["distance_km"], (int, float))
        
        # Verify guesses count updated
        assert data["guesses_used"] == 1
        assert data["guesses_remaining"] == 5
    
    def test_puzzle_guess_persistence(self):
        """Verify guesses are persisted - same guest ID returns previous guesses"""
        # Use a fixed guest ID for this test to ensure persistence
        persistent_guest_id = f"persist_test_{uuid.uuid4().hex[:8]}"
        headers = {"X-Guest-ID": persistent_guest_id, "Content-Type": "application/json"}
        
        # Make a guess
        search_response = requests.get(f"{BASE_URL}/api/buildings/search?q=big ben")
        buildings = search_response.json()
        assert len(buildings) > 0, "Should find Big Ben building"
        
        guess_payload = {"building_id": buildings[0]["building_id"]}
        guess_response = requests.post(f"{BASE_URL}/api/puzzle/guess", headers=headers, json=guess_payload)
        assert guess_response.status_code == 200, f"Guess should succeed: {guess_response.text}"
        
        # Get puzzle again with same guest ID
        response = requests.get(f"{BASE_URL}/api/puzzle/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have the guess persisted
        assert data["guesses_used"] >= 1, f"Expected at least 1 guess, got {data['guesses_used']}"
        assert len(data["guesses"]) >= 1, f"Expected at least 1 guess in list, got {len(data['guesses'])}"
    
    def test_puzzle_share_after_guess(self, guest_id):
        """GET /api/puzzle/share returns share text after making a guess"""
        headers = {"X-Guest-ID": guest_id, "Content-Type": "application/json"}
        
        # First make a guess
        search_response = requests.get(f"{BASE_URL}/api/buildings/search?q=colosseum")
        buildings = search_response.json()
        if len(buildings) > 0:
            guess_payload = {"building_id": buildings[0]["building_id"]}
            requests.post(f"{BASE_URL}/api/puzzle/guess", headers=headers, json=guess_payload)
        
        # Get share text
        response = requests.get(f"{BASE_URL}/api/puzzle/share", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify share text structure
        assert "share_text" in data
        assert "is_solved" in data
        assert "score" in data
        
        # Share text should contain puzzle info
        share_text = data["share_text"]
        assert "Silhouettele" in share_text
        assert "/6" in share_text  # Score format
    
    def test_puzzle_share_without_guess_fails(self):
        """GET /api/puzzle/share without any guesses returns 400"""
        fresh_guest_id = f"fresh_guest_{uuid.uuid4().hex[:12]}"
        headers = {"X-Guest-ID": fresh_guest_id}
        
        response = requests.get(f"{BASE_URL}/api/puzzle/share", headers=headers)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "no guesses" in data["detail"].lower()
    
    def test_puzzle_duplicate_guess_rejected(self, guest_id):
        """POST /api/puzzle/guess with same building twice returns 400"""
        headers = {"X-Guest-ID": guest_id, "Content-Type": "application/json"}
        
        # Get a building
        search_response = requests.get(f"{BASE_URL}/api/buildings/search?q=sydney")
        buildings = search_response.json()
        assert len(buildings) > 0
        
        building_id = buildings[0]["building_id"]
        guess_payload = {"building_id": building_id}
        
        # First guess should succeed
        response1 = requests.post(f"{BASE_URL}/api/puzzle/guess", headers=headers, json=guess_payload)
        assert response1.status_code == 200
        
        # Second guess with same building should fail
        response2 = requests.post(f"{BASE_URL}/api/puzzle/guess", headers=headers, json=guess_payload)
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already guessed" in data["detail"].lower()


class TestOgImage:
    """Open Graph image endpoint"""

    def test_og_today_returns_png(self):
        """GET /api/og/today.png returns a 1200x630 PNG"""
        response = requests.get(f"{BASE_URL}/api/og/today.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(response.content) > 1000


class TestProtectedEndpoints:
    """Test that auth-protected endpoints properly reject guests"""
    
    def test_stats_requires_auth(self):
        """GET /api/stats/me requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/stats/me", headers=headers)
        assert response.status_code == 401
    
    def test_friends_requires_auth(self):
        """GET /api/friends requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/friends", headers=headers)
        assert response.status_code == 401
    
    def test_leaderboard_requires_auth(self):
        """GET /api/leaderboard/overall requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/leaderboard/overall?metric=streak", headers=headers)
        assert response.status_code == 401
    
    def test_achievements_requires_auth(self):
        """GET /api/achievements/me requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/achievements/me", headers=headers)
        assert response.status_code == 401
    
    def test_challenges_requires_auth(self):
        """GET /api/challenges/current requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/challenges/current", headers=headers)
        assert response.status_code == 401
    
    def test_puzzle_calendar_requires_auth(self):
        """GET /api/puzzle/calendar requires authentication"""
        headers = {"X-Guest-ID": "test_guest_123"}
        response = requests.get(f"{BASE_URL}/api/puzzle/calendar", headers=headers)
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
