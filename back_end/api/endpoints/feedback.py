from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.schemas import FeedbackCreate, FeedbackResponse
from api.services import FeedbackService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(feedback: FeedbackCreate, user_id: int, db: Session = Depends(get_db)):
    """Create new feedback."""
    new_feedback = FeedbackService.create_feedback(db, feedback, user_id)
    return new_feedback

@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get feedback by ID."""
    feedback = FeedbackService.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    return feedback

@router.get("/event/{event_id}")
async def get_event_feedback(event_id: int, db: Session = Depends(get_db)):
    """Get all feedback for a draft event."""
    feedback_list = FeedbackService.get_feedback_for_event(db, event_id)
    return feedback_list

@router.get("/user/{user_id}")
async def get_user_feedback(user_id: int, db: Session = Depends(get_db)):
    """Get all feedback from a user."""
    feedback_list = FeedbackService.get_user_feedback(db, user_id)
    return feedback_list

@router.delete("/{feedback_id}")
async def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Delete feedback."""
    success = FeedbackService.delete_feedback(db, feedback_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    return {"message": "Feedback deleted successfully"}

@router.get("/event/{event_id}/average-rating")
async def get_event_average_rating(event_id: int, db: Session = Depends(get_db)):
    """Get the average rating for a draft event."""
    avg_rating = FeedbackService.get_average_rating_for_event(db, event_id)
    if avg_rating is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback found for this event"
        )
    return {"average_rating": avg_rating}
