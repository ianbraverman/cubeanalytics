from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.schemas import CubeCardCreate, CubeCardResponse
from api.services import CubeCardService, CardService, CubeService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/{cube_id}/add-card", response_model=CubeCardResponse)
async def add_card_to_cube(
    cube_id: int,
    cube_card: CubeCardCreate,
    db: Session = Depends(get_db)
):
    """Add a card to a cube."""
    # Check if cube exists
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    
    # Check if card exists
    card = CardService.get_card_by_id(db, cube_card.card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    new_cube_card = CubeCardService.add_card_to_cube(db, cube_id, cube_card)
    return new_cube_card

@router.get("/{cube_id}/cards", response_model=list[CubeCardResponse])
async def get_cube_cards(cube_id: int, db: Session = Depends(get_db)):
    """Get all cards in a cube."""
    # Check if cube exists
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    
    cube_cards = CubeCardService.get_cards_in_cube(db, cube_id)
    return cube_cards

@router.get("/{cube_id}/size")
async def get_cube_size(cube_id: int, db: Session = Depends(get_db)):
    """Get the total number of cards in a cube."""
    # Check if cube exists
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    
    size = CubeCardService.get_cube_size(db, cube_id)
    return {"cube_id": cube_id, "total_cards": size}

@router.delete("/{cube_id}/remove-card/{card_id}")
async def remove_card_from_cube(
    cube_id: int,
    card_id: int,
    db: Session = Depends(get_db)
):
    """Remove a card from a cube."""
    success = CubeCardService.remove_card_from_cube(db, cube_id, card_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in this cube"
        )
    return {"message": "Card removed from cube"}

@router.delete("/{cube_id}/clear-all")
async def clear_all_cards_from_cube(
    cube_id: int,
    db: Session = Depends(get_db)
):
    """Delete all cards from a cube."""
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    
    count = CubeCardService.delete_all_cards_from_cube(db, cube_id)
    return {"message": f"Deleted {count} cards from cube"}

@router.post("/{cube_id}/bulk-add")
async def bulk_add_cards_to_cube(
    cube_id: int,
    card_ids: list[int],
    db: Session = Depends(get_db),
):
    """Add multiple cards to a cube in a single request.
    
    Skips cards that are already in the cube (no duplicates) and skips
    card IDs that don't exist in the database.
    Returns counts of added and skipped cards.
    """
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cube not found")

    from api.models import CubeCard

    # Build a lookup of existing cube-card rows keyed by card_id so we can
    # increment quantity for cards already present (supports non-singleton cubes).
    existing: dict[int, CubeCard] = {
        cc.card_id: cc
        for cc in db.query(CubeCard).filter(CubeCard.cube_id == cube_id).all()
    }

    added = 0
    skipped = 0  # only incremented when the card_id doesn't exist in our DB

    for card_id in card_ids:
        if card_id in existing:
            # Non-singleton support: increment the quantity of the existing row
            existing[card_id].quantity += 1
            added += 1
        else:
            card = CardService.get_card_by_id(db, card_id)
            if not card:
                skipped += 1
                continue
            new_cc = CubeCard(cube_id=cube_id, card_id=card_id, quantity=1)
            db.add(new_cc)
            existing[card_id] = new_cc
            added += 1

    db.commit()
    return {"added": added, "skipped": skipped}


@router.delete("/{cube_id}/decrement-card/{card_id}")
async def decrement_card_in_cube(
    cube_id: int,
    card_id: int,
    db: Session = Depends(get_db),
):
    """Decrement the quantity of a card in a cube by 1.
    Removes the row entirely when quantity reaches 0.
    """
    from api.models import CubeCard
    db_cube_card = db.query(CubeCard).filter(
        CubeCard.cube_id == cube_id,
        CubeCard.card_id == card_id,
    ).first()

    if not db_cube_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in this cube",
        )

    if db_cube_card.quantity > 1:
        db_cube_card.quantity -= 1
        db.commit()
        return {"message": "Card quantity decremented", "quantity": db_cube_card.quantity}
    else:
        db.delete(db_cube_card)
        db.commit()
        return {"message": "Card removed from cube", "quantity": 0}


@router.put("/{cube_id}/update-card/{card_id}")
async def update_card_quantity(
    cube_id: int,
    card_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):
    """Update the quantity of a card in a cube."""
    if quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be at least 1"
        )
    
    updated = CubeCardService.update_card_quantity(db, cube_id, card_id, quantity)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in this cube"
        )
    return updated
