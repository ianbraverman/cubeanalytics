import json
from typing import Optional
from sqlalchemy.orm import Session
from api.models import UserDeck, Card
from api.schemas import UserDeckCreate, UserDeckUpdate

_COLOR_ORDER = "WUBRG"


class UserDeckService:
    """Service class for user deck-related operations."""

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _serialize(lst: list | None) -> str | None:
        return json.dumps(lst) if lst is not None else None

    @staticmethod
    def _deserialize(text: str | None) -> list:
        if not text:
            return []
        try:
            return json.loads(text)
        except Exception:
            return []

    @staticmethod
    def compute_color_identity(db: Session, card_ids: list[int]) -> str:
        """Return a WUBRG-ordered color string for the given card IDs (e.g. 'WR', 'UB', 'C')."""
        if not card_ids:
            return "C"
        cards = db.query(Card.colors).filter(Card.id.in_(card_ids)).all()
        seen: set[str] = set()
        for (colors,) in cards:
            if colors:
                for c in colors:
                    upper = c.upper()
                    if upper in _COLOR_ORDER:
                        seen.add(upper)
        return "".join(c for c in _COLOR_ORDER if c in seen) or "C"

    # ------------------------------------------------------------------ CRUD
    @staticmethod
    def create_user_deck(db: Session, deck: UserDeckCreate, user_id: Optional[int]) -> UserDeck:
        record = deck.record or f"{deck.wins or 0}-{deck.losses or 0}"
        color_identity = deck.color_identity
        if color_identity is None and deck.deck_cards:
            color_identity = UserDeckService.compute_color_identity(db, deck.deck_cards)
        db_deck = UserDeck(
            user_id=user_id,
            draft_event_id=deck.draft_event_id,
            player_name=deck.player_name,
            deck_name=deck.deck_name,
            deck_cards=UserDeckService._serialize(deck.deck_cards),
            sideboard_cards=UserDeckService._serialize(deck.sideboard_cards),
            full_pool_cards=UserDeckService._serialize(deck.full_pool_cards),
            wins=deck.wins or 0,
            losses=deck.losses or 0,
            record=record,
            archetype=deck.archetype,
            archetype_detail=deck.archetype_detail,
            color_identity=color_identity,
        )
        db.add(db_deck)
        db.commit()
        db.refresh(db_deck)
        return db_deck

    @staticmethod
    def update_user_deck(db: Session, deck_id: int, update: UserDeckUpdate) -> UserDeck | None:
        deck = db.query(UserDeck).filter(UserDeck.id == deck_id).first()
        if not deck:
            return None
        data = update.model_dump(exclude_unset=True)
        for field in ("deck_cards", "sideboard_cards", "full_pool_cards"):
            if field in data:
                setattr(deck, field, UserDeckService._serialize(data.pop(field)))
        for field, value in data.items():
            setattr(deck, field, value)
        # auto-sync record from wins/losses
        deck.record = f"{deck.wins or 0}-{deck.losses or 0}"
        # recompute color_identity if deck_cards changed and color_identity not explicitly provided
        if "deck_cards" in (update.model_fields_set if hasattr(update, "model_fields_set") else set()) \
                and "color_identity" not in (update.model_fields_set if hasattr(update, "model_fields_set") else set()):
            card_ids = UserDeckService._deserialize(deck.deck_cards)
            deck.color_identity = UserDeckService.compute_color_identity(db, card_ids)
        db.commit()
        db.refresh(deck)
        return deck

    @staticmethod
    def deck_to_dict(deck: UserDeck) -> dict:
        """Convert ORM object to a plain dict for serialization."""
        return {
            "id": deck.id,
            "user_id": deck.user_id,
            "draft_event_id": deck.draft_event_id,
            "player_name": deck.player_name,
            "deck_name": deck.deck_name,
            "deck_cards": UserDeckService._deserialize(deck.deck_cards),
            "sideboard_cards": UserDeckService._deserialize(deck.sideboard_cards),
            "full_pool_cards": UserDeckService._deserialize(deck.full_pool_cards),
            "wins": deck.wins or 0,
            "losses": deck.losses or 0,
            "record": deck.record,
            "deck_photo_url": deck.deck_photo_url,
            "pool_photo_url": deck.pool_photo_url,
            "ai_description": deck.ai_description,
            "archetype": deck.archetype,
            "archetype_detail": deck.archetype_detail,
            "color_identity": deck.color_identity,
            "created_at": deck.created_at,
        }

    @staticmethod
    def get_user_deck_by_id(db: Session, deck_id: int) -> UserDeck | None:
        return db.query(UserDeck).filter(UserDeck.id == deck_id).first()

    @staticmethod
    def get_decks_for_event(db: Session, event_id: int) -> list[UserDeck]:
        return db.query(UserDeck).filter(UserDeck.draft_event_id == event_id).all()

    @staticmethod
    def delete_user_deck(db: Session, deck_id: int) -> bool:
        db_deck = UserDeckService.get_user_deck_by_id(db, deck_id)
        if db_deck:
            db.delete(db_deck)
            db.commit()
            return True
        return False
