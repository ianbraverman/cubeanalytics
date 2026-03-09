from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Card Schemas
class CardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scryfall_id: str = Field(..., min_length=1)

class CardCreate(CardBase):
    pass

class CardResponse(CardBase):
    id: int
    mana_cost: Optional[str] = None
    type_line: Optional[str] = None
    colors: Optional[list[str]] = None
    cmc: Optional[float] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    oracle_text: Optional[str] = None
    image_url: Optional[str] = None
    small_image_url: Optional[str] = None
    rarity: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    scryfall_uri: Optional[str] = None
    cached_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Cube Card Schemas (for many-to-many relationship)
class CubeCardCreate(BaseModel):
    card_id: int
    quantity: int = Field(default=1, ge=1)

class CubeCardResponse(BaseModel):
    id: int
    cube_id: int
    card_id: int
    quantity: int
    card: CardResponse

    class Config:
        from_attributes = True

# Cube Schemas
class CubeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CubeCreate(CubeBase):
    pass

class CubeSettingsUpdate(BaseModel):
    life_total: Optional[int] = Field(None, ge=1, le=999)
    pack_count: Optional[int] = Field(None, ge=1, le=20)
    pack_size: Optional[int] = Field(None, ge=1, le=100)
    draft_rules: Optional[str] = None
    gameplay_rules: Optional[str] = None

class CubeResponse(CubeBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    life_total: int = 20
    pack_count: int = 3
    pack_size: int = 15
    draft_rules: Optional[str] = None
    gameplay_rules: Optional[str] = None

    class Config:
        from_attributes = True

class CubeWithCardsResponse(CubeResponse):
    cube_cards: list[CubeCardResponse]

    class Config:
        from_attributes = True

# Draft Event Schemas
class DraftParticipantResponse(BaseModel):
    user_id: int
    username: str
    joined_at: datetime

class DraftEventBase(BaseModel):
    cube_id: int
    password: str = Field(..., min_length=6)

class DraftEventCreate(DraftEventBase):
    name: Optional[str] = None
    num_players: Optional[int] = None
    event_type: Optional[str] = "casual"   # casual | hosted
    num_rounds: Optional[int] = None
    best_of: Optional[int] = 1             # 1, 3, or 5

class DraftEventUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    num_players: Optional[int] = None
    ai_summary: Optional[str] = None
    event_type: Optional[str] = None
    num_rounds: Optional[int] = None
    best_of: Optional[int] = None
    current_round: Optional[int] = None

class DraftEventResponse(BaseModel):
    id: int
    cube_id: int
    name: Optional[str] = None
    status: Optional[str] = None
    num_players: Optional[int] = None
    ai_summary: Optional[str] = None
    event_type: str = "casual"
    num_rounds: Optional[int] = None
    best_of: int = 1
    current_round: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# User Deck Schemas
class UserDeckCreate(BaseModel):
    draft_event_id: int
    user_id: Optional[int] = None        # if provided, use real user's ID
    player_name: Optional[str] = None
    deck_name: Optional[str] = None
    deck_cards: list[int] = []          # list of card IDs
    sideboard_cards: Optional[list[int]] = None
    full_pool_cards: Optional[list[int]] = None
    wins: Optional[int] = 0
    losses: Optional[int] = 0
    record: Optional[str] = None

class UserDeckUpdate(BaseModel):
    player_name: Optional[str] = None
    deck_name: Optional[str] = None
    deck_cards: Optional[list[int]] = None
    sideboard_cards: Optional[list[int]] = None
    full_pool_cards: Optional[list[int]] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    record: Optional[str] = None
    deck_photo_url: Optional[str] = None
    pool_photo_url: Optional[str] = None
    ai_description: Optional[str] = None

class UserDeckResponse(BaseModel):
    id: int
    user_id: int
    draft_event_id: int
    player_name: Optional[str] = None
    deck_name: Optional[str] = None
    deck_cards: list[int] = []
    sideboard_cards: Optional[list[int]] = None
    full_pool_cards: Optional[list[int]] = None
    wins: int = 0
    losses: int = 0
    record: Optional[str] = None
    deck_photo_url: Optional[str] = None
    pool_photo_url: Optional[str] = None
    ai_description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DraftEventWithDecksResponse(DraftEventResponse):
    user_decks: list[UserDeckResponse] = []

    class Config:
        from_attributes = True

# Seating
class DraftSeatResponse(BaseModel):
    user_id: int
    username: str
    seat_number: int

# Pairing / Round
class SubmitMatchResult(BaseModel):
    player1_wins: int = Field(0, ge=0)
    player2_wins: int = Field(0, ge=0)
    submitting_user_id: Optional[int] = None

class DraftPairingResponse(BaseModel):
    id: int
    player1_user_id: Optional[int]
    player2_user_id: Optional[int]
    player1_name: Optional[str]
    player2_name: Optional[str]
    player1_deck_id: Optional[int]
    player2_deck_id: Optional[int]
    player1_wins: int
    player2_wins: int
    winner_user_id: Optional[int]
    player1_confirmed: str
    player2_confirmed: str
    status: str

class DraftRoundResponse(BaseModel):
    id: int
    round_number: int
    status: str
    pairings: List[DraftPairingResponse]

# Round Feedback
class RoundFeedbackCreate(BaseModel):
    user_id: int
    liked_card_ids: Optional[list[int]] = None
    disliked_card_ids: Optional[list[int]] = None
    liked_notes: Optional[str] = None
    disliked_notes: Optional[str] = None
    general_thoughts: Optional[str] = None

class RoundFeedbackResponse(BaseModel):
    id: int
    pairing_id: int
    user_id: int
    liked_card_ids: Optional[list[int]]
    disliked_card_ids: Optional[list[int]]
    liked_notes: Optional[str]
    disliked_notes: Optional[str]
    general_thoughts: Optional[str]
    created_at: datetime

# Post-Draft Feedback
class PostDraftFeedbackCreate(BaseModel):
    user_id: Optional[int] = None
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    overall_thoughts: Optional[str] = None
    standout_card_ids: Optional[list[int]] = None
    underperformer_card_ids: Optional[list[int]] = None
    recommendations_for_owner: Optional[str] = None

class PostDraftFeedbackResponse(BaseModel):
    id: int
    draft_event_id: int
    user_id: int
    overall_rating: Optional[int]
    overall_thoughts: Optional[str]
    standout_card_ids: Optional[list[int]]
    underperformer_card_ids: Optional[list[int]]
    recommendations_for_owner: Optional[str]
    created_at: datetime

# Feedback Schema
class FeedbackBase(BaseModel):
    draft_event_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=500)

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackResponse(FeedbackBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Card Feedback Schemas
class CardFeedbackBase(BaseModel):
    card_id: int
    feedback_type: str = Field(..., pattern="^(cube_specific|general)$")
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=1000)

class CardFeedbackCreate(CardFeedbackBase):
    draft_event_id: Optional[int] = None

class CardFeedbackResponse(CardFeedbackBase):
    id: int
    user_id: int
    draft_event_id: Optional[int]
    vector_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Card Schemas
class CardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scryfall_id: str = Field(..., min_length=1)

class CardCreate(CardBase):
    pass

class CardResponse(CardBase):
    id: int
    mana_cost: Optional[str] = None
    type_line: Optional[str] = None
    colors: Optional[list[str]] = None
    cmc: Optional[float] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    oracle_text: Optional[str] = None
    image_url: Optional[str] = None
    small_image_url: Optional[str] = None
    rarity: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    scryfall_uri: Optional[str] = None
    cached_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Cube Card Schemas (for many-to-many relationship)
class CubeCardCreate(BaseModel):
    card_id: int
    quantity: int = Field(default=1, ge=1)

class CubeCardResponse(BaseModel):
    id: int
    cube_id: int
    card_id: int
    quantity: int
    card: CardResponse

    class Config:
        from_attributes = True

# Cube Schemas
class CubeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CubeCreate(CubeBase):
    pass

class CubeResponse(CubeBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CubeWithCardsResponse(CubeResponse):
    cube_cards: list[CubeCardResponse]

    class Config:
        from_attributes = True
