from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class DraftParticipant(Base):
    __tablename__ = "draft_participants"

    id = Column(Integer, primary_key=True, index=True)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft_event = relationship("DraftEvent", back_populates="participants")
    user = relationship("User", back_populates="draft_participations")
