from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class DraftSeat(Base):
    """Assigned seat number for each player in a hosted draft event."""
    __tablename__ = "draft_seats"

    id = Column(Integer, primary_key=True, index=True)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seat_number = Column(Integer, nullable=False)   # 1-indexed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft_event = relationship("DraftEvent", back_populates="seats")
    user = relationship("User")
