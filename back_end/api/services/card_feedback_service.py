from sqlalchemy.orm import Session
from api.models import CardFeedback, Card
from api.schemas import CardFeedbackCreate
from api.services.vector_service import VectorService

class CardFeedbackService:
    """Service class for card feedback operations."""

    @staticmethod
    def create_card_feedback(
        db: Session,
        feedback: CardFeedbackCreate,
        user_id: int
    ) -> CardFeedback:
        """Create new card feedback and vectorize it."""
        # Create the feedback record
        db_feedback = CardFeedback(
            user_id=user_id,
            card_id=feedback.card_id,
            draft_event_id=feedback.draft_event_id,
            feedback_type=feedback.feedback_type,
            rating=feedback.rating,
            comment=feedback.comment
        )
        
        # Get the card to use its name
        card = db.query(Card).filter(Card.id == feedback.card_id).first()
        
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        # Vectorize the feedback in Chroma DB
        if card:
            vector_id = VectorService.add_feedback_vector(
                feedback_id=db_feedback.id,
                card_name=card.name,
                feedback_text=feedback.comment,
                feedback_type=feedback.feedback_type,
                rating=feedback.rating,
                user_id=user_id
            )
            
            # Update the feedback record with the vector ID
            db_feedback.vector_id = vector_id
            db.commit()
        
        return db_feedback

    @staticmethod
    def get_card_feedback_by_id(db: Session, feedback_id: int) -> CardFeedback | None:
        """Get card feedback by ID."""
        return db.query(CardFeedback).filter(CardFeedback.id == feedback_id).first()

    @staticmethod
    def get_feedback_for_card(db: Session, card_id: int, limit: int = 50) -> list[CardFeedback]:
        """Get all feedback for a specific card."""
        return db.query(CardFeedback).filter(CardFeedback.card_id == card_id).limit(limit).all()

    @staticmethod
    def get_user_card_feedback(db: Session, user_id: int) -> list[CardFeedback]:
        """Get all card feedback from a user."""
        return db.query(CardFeedback).filter(CardFeedback.user_id == user_id).all()

    @staticmethod
    def get_feedback_by_type(
        db: Session,
        card_id: int,
        feedback_type: str
    ) -> list[CardFeedback]:
        """Get feedback for a card by type (cube_specific or general)."""
        return db.query(CardFeedback).filter(
            CardFeedback.card_id == card_id,
            CardFeedback.feedback_type == feedback_type
        ).all()

    @staticmethod
    def get_average_rating_for_card(
        db: Session,
        card_id: int,
        feedback_type: str | None = None
    ) -> float | None:
        """Get average rating for a card, optionally by feedback type."""
        query = db.query(CardFeedback).filter(CardFeedback.card_id == card_id)
        
        if feedback_type:
            query = query.filter(CardFeedback.feedback_type == feedback_type)
        
        feedback_list = query.all()
        
        if feedback_list:
            avg_rating = sum(f.rating for f in feedback_list) / len(feedback_list)
            return round(avg_rating, 2)
        
        return None

    @staticmethod
    def delete_card_feedback(db: Session, feedback_id: int) -> bool:
        """Delete card feedback and its vector."""
        db_feedback = CardFeedbackService.get_card_feedback_by_id(db, feedback_id)
        
        if db_feedback:
            # Delete from vector database
            if db_feedback.vector_id:
                VectorService.delete_feedback_vector(feedback_id)
            
            # Delete from SQL database
            db.delete(db_feedback)
            db.commit()
            return True
        
        return False

    @staticmethod
    def query_similar_cards(
        query_text: str,
        feedback_type: str | None = None,
        n_results: int = 5
    ) -> dict:
        """Query for similar card feedback using vector similarity."""
        return VectorService.query_similar_feedback(
            query_text=query_text,
            feedback_type=feedback_type,
            n_results=n_results
        )

    @staticmethod
    def get_card_feedback_summary(db: Session, card_id: int) -> dict:
        """Get a summary of all feedback for a card."""
        feedback_list = CardFeedbackService.get_feedback_for_card(db, card_id)
        
        if not feedback_list:
            return {}
        
        general_feedback = [f for f in feedback_list if f.feedback_type == "general"]
        cube_feedback = [f for f in feedback_list if f.feedback_type == "cube_specific"]
        
        summary = {
            "total_feedback_count": len(feedback_list),
            "general": {
                "count": len(general_feedback),
                "average_rating": sum(f.rating for f in general_feedback) / len(general_feedback) if general_feedback else None
            },
            "cube_specific": {
                "count": len(cube_feedback),
                "average_rating": sum(f.rating for f in cube_feedback) / len(cube_feedback) if cube_feedback else None
            }
        }
        
        return summary
