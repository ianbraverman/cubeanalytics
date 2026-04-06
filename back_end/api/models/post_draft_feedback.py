from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class PostDraftFeedback(Base):
    """Overall post-draft feedback from each participating player."""
    __tablename__ = "post_draft_feedback"

    id = Column(Integer, primary_key=True, index=True)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # nullable for organizer-entered feedback
    player_name = Column(String, nullable=True)                   # display name when no user_id
    overall_rating = Column(Integer, nullable=True)               # 1-5
    overall_thoughts = Column(Text, nullable=True)                # freeform
    # JSON lists of card IDs
    standout_card_ids = Column(Text, nullable=True)               # cards that stood out
    underperformer_card_ids = Column(Text, nullable=True)         # cards that disappointed
    recommendations_for_owner = Column(Text, nullable=True)       # cut/add suggestions
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft_event = relationship("DraftEvent", back_populates="post_draft_feedback")
    user = relationship("User")
