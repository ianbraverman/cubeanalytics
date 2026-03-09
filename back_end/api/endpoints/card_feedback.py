from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from api.schemas import CardFeedbackCreate, CardFeedbackResponse
from api.services import CardFeedbackService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=CardFeedbackResponse)
async def create_card_feedback(
    feedback: CardFeedbackCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create new card feedback."""
    new_feedback = CardFeedbackService.create_card_feedback(db, feedback, user_id)
    return new_feedback

@router.get("/{feedback_id}", response_model=CardFeedbackResponse)
async def get_card_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get card feedback by ID."""
    feedback = CardFeedbackService.get_card_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    return feedback

@router.get("/card/{card_id}")
async def get_feedback_for_card(
    card_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all feedback for a card."""
    feedback_list = CardFeedbackService.get_feedback_for_card(db, card_id, limit=limit)
    return feedback_list

@router.get("/user/{user_id}")
async def get_user_card_feedback(user_id: int, db: Session = Depends(get_db)):
    """Get all card feedback from a user."""
    feedback_list = CardFeedbackService.get_user_card_feedback(db, user_id)
    return feedback_list

@router.get("/card/{card_id}/type/{feedback_type}")
async def get_feedback_by_type(
    card_id: int,
    feedback_type: str,
    db: Session = Depends(get_db)
):
    """Get card feedback by type (cube_specific or general)."""
    if feedback_type not in ["cube_specific", "general"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback type. Must be 'cube_specific' or 'general'"
        )
    
    feedback_list = CardFeedbackService.get_feedback_by_type(db, card_id, feedback_type)
    return feedback_list

@router.get("/card/{card_id}/average-rating")
async def get_card_average_rating(
    card_id: int,
    feedback_type: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Get average rating for a card, optionally by feedback type."""
    if feedback_type and feedback_type not in ["cube_specific", "general"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback type. Must be 'cube_specific' or 'general'"
        )
    
    avg_rating = CardFeedbackService.get_average_rating_for_card(db, card_id, feedback_type)
    
    if avg_rating is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback found for this card"
        )
    
    return {"average_rating": avg_rating}

@router.get("/card/{card_id}/summary")
async def get_card_feedback_summary(card_id: int, db: Session = Depends(get_db)):
    """Get a summary of all feedback for a card."""
    summary = CardFeedbackService.get_card_feedback_summary(db, card_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback found for this card"
        )
    
    return summary

@router.post("/search")
async def search_similar_cards(
    query_text: str,
    feedback_type: str | None = Query(None),
    n_results: int = Query(5, ge=1, le=20)
):
    """Search for similar card feedback using vector similarity."""
    if feedback_type and feedback_type not in ["cube_specific", "general"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback type. Must be 'cube_specific' or 'general'"
        )
    
    results = CardFeedbackService.query_similar_cards(
        query_text=query_text,
        feedback_type=feedback_type,
        n_results=n_results
    )
    
    return results

@router.delete("/{feedback_id}")
async def delete_card_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Delete card feedback."""
    success = CardFeedbackService.delete_card_feedback(db, feedback_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    return {"message": "Feedback deleted successfully"}
