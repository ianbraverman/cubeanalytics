from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.schemas import UserDeckCreate, UserDeckResponse
from api.services import UserDeckService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=UserDeckResponse)
async def create_user_deck(deck: UserDeckCreate, user_id: int, db: Session = Depends(get_db)):
    """Create a new user deck."""
    new_deck = UserDeckService.create_user_deck(db, deck, user_id)
    return new_deck

@router.get("/{deck_id}", response_model=UserDeckResponse)
async def get_user_deck(deck_id: int, db: Session = Depends(get_db)):
    """Get a user deck by ID."""
    deck = UserDeckService.get_user_deck_by_id(db, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    return deck

@router.get("/user/{user_id}")
async def get_user_decks(user_id: int, db: Session = Depends(get_db)):
    """Get all decks for a user."""
    decks = UserDeckService.get_user_decks(db, user_id)
    return decks

@router.get("/event/{event_id}")
async def get_event_decks(event_id: int, db: Session = Depends(get_db)):
    """Get all decks for a draft event."""
    decks = UserDeckService.get_decks_for_event(db, event_id)
    return decks

@router.delete("/{deck_id}")
async def delete_user_deck(deck_id: int, db: Session = Depends(get_db)):
    """Delete a user deck."""
    success = UserDeckService.delete_user_deck(db, deck_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    return {"message": "Deck deleted successfully"}

@router.get("/{deck_id}/cards")
async def get_deck_cards(deck_id: int, db: Session = Depends(get_db)):
    """Get the cards from a deck."""
    cards = UserDeckService.get_deck_cards(db, deck_id)
    if cards is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    return cards
