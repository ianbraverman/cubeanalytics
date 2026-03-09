from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class DraftEvent(Base):
    __tablename__ = "draft_events"

    id = Column(Integer, primary_key=True, index=True)
    cube_id = Column(Integer, ForeignKey("cubes.id"), nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String(200), nullable=True)
    # status: active | seating_assigned | drafting | deck_submission | in_rounds | completed
    status = Column(String(30), default="active")
    num_players = Column(Integer, default=0)
    ai_summary = Column(Text, nullable=True)            # AI narrative of the draft
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Hosted event fields
    event_type = Column(String(20), default="casual")   # casual | hosted
    num_rounds = Column(Integer, nullable=True)         # number of Swiss rounds
    best_of = Column(Integer, default=1)                # 1, 3, or 5
    current_round = Column(Integer, default=0)          # 0 = pre-start

    # Relationships
    cube = relationship("Cube", back_populates="draft_events")
    user_decks = relationship("UserDeck", back_populates="draft_event", cascade="all, delete")
    participants = relationship("DraftParticipant", back_populates="draft_event", cascade="all, delete")
    feedback = relationship("Feedback", back_populates="draft_event")
    card_feedback = relationship("CardFeedback", back_populates="draft_event")
    seats = relationship("DraftSeat", back_populates="draft_event", cascade="all, delete")
    rounds = relationship("DraftRound", back_populates="draft_event", cascade="all, delete")
    post_draft_feedback = relationship("PostDraftFeedback", back_populates="draft_event", cascade="all, delete")
