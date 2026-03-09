from sqlalchemy.orm import Session
from api.models import Feedback
from api.schemas import FeedbackCreate

class FeedbackService:
    """Service class for feedback-related operations."""

    @staticmethod
    def create_feedback(db: Session, feedback: FeedbackCreate, user_id: int) -> Feedback:
        """Create new feedback in the database."""
        db_feedback = Feedback(
            user_id=user_id,
            draft_event_id=feedback.draft_event_id,
            rating=feedback.rating,
            comment=feedback.comment
        )
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        return db_feedback

    @staticmethod
    def get_feedback_by_id(db: Session, feedback_id: int) -> Feedback | None:
        """Get feedback by ID."""
        return db.query(Feedback).filter(Feedback.id == feedback_id).first()

    @staticmethod
    def get_feedback_for_event(db: Session, event_id: int) -> list[Feedback]:
        """Get all feedback for a draft event."""
        return db.query(Feedback).filter(Feedback.draft_event_id == event_id).all()

    @staticmethod
    def get_user_feedback(db: Session, user_id: int) -> list[Feedback]:
        """Get all feedback from a user."""
        return db.query(Feedback).filter(Feedback.user_id == user_id).all()

    @staticmethod
    def delete_feedback(db: Session, feedback_id: int) -> bool:
        """Delete feedback."""
        db_feedback = FeedbackService.get_feedback_by_id(db, feedback_id)
        if db_feedback:
            db.delete(db_feedback)
            db.commit()
            return True
        return False

    @staticmethod
    def get_average_rating_for_event(db: Session, event_id: int) -> float | None:
        """Get the average rating for a draft event."""
        feedback_list = FeedbackService.get_feedback_for_event(db, event_id)
        if feedback_list:
            total_rating = sum(f.rating for f in feedback_list)
            return total_rating / len(feedback_list)
        return None
