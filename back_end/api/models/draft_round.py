from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class DraftRound(Base):
    """A single round of a hosted draft event."""
    __tablename__ = "draft_rounds"

    id = Column(Integer, primary_key=True, index=True)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=False)
    round_number = Column(Integer, nullable=False)                 # 1-indexed
    status = Column(String(20), default="active")                 # active | complete
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft_event = relationship("DraftEvent", back_populates="rounds")
    pairings = relationship("DraftPairing", back_populates="round", cascade="all, delete")


class DraftPairing(Base):
    """A single match pairing within a draft round."""
    __tablename__ = "draft_pairings"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("draft_rounds.id"), nullable=False)
    # player1 / player2 are user_ids; one can be None for a bye
    player1_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player2_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Deck IDs for reference
    player1_deck_id = Column(Integer, ForeignKey("user_decks.id"), nullable=True)
    player2_deck_id = Column(Integer, ForeignKey("user_decks.id"), nullable=True)
    # Individual game wins per player within the match
    player1_wins = Column(Integer, default=0)
    player2_wins = Column(Integer, default=0)
    # who won the match (user_id or None for draw/bye)
    winner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # both players must confirm the result
    player1_confirmed = Column(String(5), default="no")   # yes | no
    player2_confirmed = Column(String(5), default="no")   # yes | no
    status = Column(String(20), default="pending")        # pending | disputed | complete
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    round = relationship("DraftRound", back_populates="pairings")
    player1 = relationship("User", foreign_keys=[player1_user_id])
    player2 = relationship("User", foreign_keys=[player2_user_id])
    winner = relationship("User", foreign_keys=[winner_user_id])
    player1_deck = relationship("UserDeck", foreign_keys=[player1_deck_id])
    player2_deck = relationship("UserDeck", foreign_keys=[player2_deck_id])
    feedback_entries = relationship("RoundFeedback", back_populates="pairing", cascade="all, delete")


class RoundFeedback(Base):
    """Per-player round feedback after each pairing."""
    __tablename__ = "round_feedback"

    id = Column(Integer, primary_key=True, index=True)
    pairing_id = Column(Integer, ForeignKey("draft_pairings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # JSON lists of card IDs from the cube
    liked_card_ids = Column(Text, nullable=True)       # JSON [card_id, ...]
    disliked_card_ids = Column(Text, nullable=True)    # JSON [card_id, ...]
    liked_notes = Column(Text, nullable=True)          # why they liked those cards
    disliked_notes = Column(Text, nullable=True)       # why they disliked those cards
    general_thoughts = Column(Text, nullable=True)     # freeform round thoughts
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    pairing = relationship("DraftPairing", back_populates="feedback_entries")
    user = relationship("User")
