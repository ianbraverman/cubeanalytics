from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from api.schemas import CardCreate, CardResponse
from api.services import CardService, ScryfallService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=CardResponse)
async def create_card(card: CardCreate, db: Session = Depends(get_db)):
    """Create a new card."""
    # Check if card already exists
    existing_card = CardService.get_card_by_name(db, card.name)
    if existing_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card already exists"
        )
    
    new_card = CardService.create_card(db, card)
    return new_card

@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, db: Session = Depends(get_db)):
    """Get a card by ID."""
    card = CardService.get_card_by_id(db, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return card

@router.get("/name/{card_name}", response_model=CardResponse)
async def get_card_by_name(card_name: str, db: Session = Depends(get_db)):
    """Get a card by name."""
    card = CardService.get_card_by_name(db, card_name)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return card

@router.get("/")
async def get_all_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all cards with pagination."""
    cards = CardService.get_all_cards(db, skip=skip, limit=limit)
    return cards

@router.get("/search")
async def search_cards(
    query: str = Query(..., description="Card name to search for"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search for cards by name."""
    cards = CardService.search_cards(db, query, limit=limit)
    return cards

@router.get("/{card_id}/scryfall-info")
async def get_card_scryfall_info(
    card_id: int,
    refresh: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get card information from Scryfall (cached or fresh)."""
    card_info = ScryfallService.get_card_info_cached(db, CardService, card_id, refresh=refresh)
    if not card_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found or error fetching from Scryfall"
        )
    return card_info

@router.post("/scryfall/fetch-by-name")
async def fetch_card_from_scryfall(
    card_name: str = Query(..., description="Card name to fetch from Scryfall"),
    db: Session = Depends(get_db)
):
    """Fetch card from Scryfall by name and create in database if not exists."""
    # First check if card exists in our database
    existing_card = CardService.get_card_by_name(db, card_name)
    
    # Fetch from Scryfall
    scryfall_data = ScryfallService.get_card_by_name(card_name)
    if not scryfall_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found on Scryfall"
        )
    
    # Extract relevant info
    card_info = ScryfallService.extract_card_info(scryfall_data)
    
    if existing_card:
        # Update existing card with Scryfall details in case it was missing data
        existing_card.mana_cost = card_info.get("mana_cost")
        existing_card.type_line = card_info.get("type_line")
        existing_card.colors = card_info.get("colors")
        existing_card.cmc = card_info.get("cmc")
        existing_card.power = card_info.get("power")
        existing_card.toughness = card_info.get("toughness")
        existing_card.oracle_text = card_info.get("text")
        existing_card.image_url = card_info.get("image_url")
        existing_card.small_image_url = card_info.get("small_image_url")
        existing_card.rarity = card_info.get("rarity")
        existing_card.set_code = card_info.get("set")
        existing_card.set_name = card_info.get("set_name")
        existing_card.scryfall_uri = card_info.get("scryfall_uri")
        db.commit()
        db.refresh(existing_card)
        return {"message": "Card updated with Scryfall data", "card": existing_card}
    
    # Create new card with all details
    new_card = CardService.create_card_with_details(
        db,
        name=card_info["name"],
        scryfall_id=card_info["id"],
        mana_cost=card_info.get("mana_cost"),
        type_line=card_info.get("type_line"),
        colors=card_info.get("colors"),
        cmc=card_info.get("cmc"),
        power=card_info.get("power"),
        toughness=card_info.get("toughness"),
        oracle_text=card_info.get("text"),
        image_url=card_info.get("image_url"),
        small_image_url=card_info.get("small_image_url"),
        rarity=card_info.get("rarity"),
        set_code=card_info.get("set"),
        set_name=card_info.get("set_name"),
        scryfall_uri=card_info.get("scryfall_uri"),
    )
    
    # Cache the Scryfall data
    import json
    CardService.update_cached_data(db, new_card.id, json.dumps(card_info))
    
    return {"message": "Card created from Scryfall", "card": new_card, "card_info": card_info}

@router.post("/scryfall/search")
async def search_scryfall(
    query: str = Query(..., description="Scryfall search query"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search Scryfall directly without storing in database."""
    results = ScryfallService.search_cards(query, limit=limit)
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cards found on Scryfall matching your query"
        )
    
    # Extract relevant info from each result
    extracted_results = [ScryfallService.extract_card_info(card) for card in results]
    
    return {
        "query": query,
        "count": len(extracted_results),
        "results": extracted_results
    }

@router.post("/scryfall/bulk-fetch-by-names")
async def bulk_fetch_cards_from_scryfall(
    card_names: list[str],
    db: Session = Depends(get_db)
):
    """
    Fetch multiple cards from Scryfall by name using the /cards/collection
    endpoint (up to 75 per batch).  Creates or updates cards in the database
    and returns the DB card ids along with a list of names that were not found.
    """
    if not card_names:
        return {"cards": [], "not_found": []}

    result = ScryfallService.get_cards_by_names_bulk(card_names)
    found_scryfall = result["found"]
    not_found: list[str] = result["not_found"]

    db_cards = []
    import json as _json

    for scryfall_data in found_scryfall:
        card_info = ScryfallService.extract_card_info(scryfall_data)
        card_name = card_info.get("name")
        if not card_name:
            continue

        existing = CardService.get_card_by_name(db, card_name)
        if existing:
            # Refresh all fields from Scryfall
            existing.mana_cost = card_info.get("mana_cost")
            existing.type_line = card_info.get("type_line")
            existing.colors = card_info.get("colors")
            existing.cmc = card_info.get("cmc")
            existing.power = card_info.get("power")
            existing.toughness = card_info.get("toughness")
            existing.oracle_text = card_info.get("text")
            existing.image_url = card_info.get("image_url")
            existing.small_image_url = card_info.get("small_image_url")
            existing.rarity = card_info.get("rarity")
            existing.set_code = card_info.get("set")
            existing.set_name = card_info.get("set_name")
            existing.scryfall_uri = card_info.get("scryfall_uri")
            db_cards.append(existing)
        else:
            new_card = CardService.create_card_with_details(
                db,
                name=card_name,
                scryfall_id=card_info["id"],
                mana_cost=card_info.get("mana_cost"),
                type_line=card_info.get("type_line"),
                colors=card_info.get("colors"),
                cmc=card_info.get("cmc"),
                power=card_info.get("power"),
                toughness=card_info.get("toughness"),
                oracle_text=card_info.get("text"),
                image_url=card_info.get("image_url"),
                small_image_url=card_info.get("small_image_url"),
                rarity=card_info.get("rarity"),
                set_code=card_info.get("set"),
                set_name=card_info.get("set_name"),
                scryfall_uri=card_info.get("scryfall_uri"),
            )
            CardService.update_cached_data(db, new_card.id, _json.dumps(card_info))
            db_cards.append(new_card)

    db.commit()

    return {
        "cards": [{"id": c.id, "name": c.name} for c in db_cards],
        "not_found": not_found,
    }


@router.put("/{card_id}", response_model=CardResponse)
async def update_card(card_id: int, card: CardCreate, db: Session = Depends(get_db)):
    """Update a card."""
    updated_card = CardService.update_card(db, card_id, card)
    if not updated_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return updated_card

@router.delete("/{card_id}")
async def delete_card(card_id: int, db: Session = Depends(get_db)):
    """Delete a card."""
    success = CardService.delete_card(db, card_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return {"message": "Card deleted successfully"}
