from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class UserDeck(Base):
    __tablename__ = "user_decks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=False)
    player_name = Column(String(100), nullable=True)        # display name for this draft
    deck_name = Column(String(200), nullable=True)          # e.g. "WU Skies"
    deck_cards = Column(Text, nullable=False)               # JSON list of card IDs
    sideboard_cards = Column(Text, nullable=True)           # JSON list of card IDs
    full_pool_cards = Column(Text, nullable=True)           # JSON list – all drafted cards
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    record = Column(String, nullable=True)                  # e.g. "3-0" (derived / manual)
    deck_photo_url = Column(String(500), nullable=True)     # URL/path to deck photo
    pool_photo_url = Column(String(500), nullable=True)     # URL/path to full-pool photo
    ai_description = Column(Text, nullable=True)            # AI deck summary
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="decks")
    draft_event = relationship("DraftEvent", back_populates="user_decks")
