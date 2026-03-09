from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class CardFeedback(Base):
    __tablename__ = "card_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=True)  # Optional: feedback for a specific event
    feedback_type = Column(String, nullable=False)  # "cube_specific" or "general"
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=False)
    vector_id = Column(String, nullable=True)  # ID in Chroma DB for this feedback
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="card_feedback")
    card = relationship("Card", back_populates="feedback")
    draft_event = relationship("DraftEvent", back_populates="card_feedback")
