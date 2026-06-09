from pydantic import BaseModel
from typing import Optional


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    username: Optional[str] = None
    join_date: Optional[str] = None


class GuessRequest(BaseModel):
    building_id: str


class UsernameUpdate(BaseModel):
    username: str


class FriendRequest(BaseModel):
    friend_user_id: str


class SearchQuery(BaseModel):
    q: str
