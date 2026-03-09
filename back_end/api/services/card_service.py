from sqlalchemy.orm import Session
from api.models import Card
from api.schemas import CardCreate
from typing import Optional

class CardService:
    """Service class for card-related operations."""

    @staticmethod
    def create_card(db: Session, card: CardCreate) -> Card:
        """Create a new card in the database."""
        db_card = Card(
            name=card.name,
            scryfall_id=card.scryfall_id
        )
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        return db_card

    @staticmethod
    def create_card_with_details(
        db: Session,
        name: str,
        scryfall_id: str,
        mana_cost: Optional[str] = None,
        type_line: Optional[str] = None,
        colors: Optional[list] = None,
        cmc: Optional[float] = None,
        power: Optional[str] = None,
        toughness: Optional[str] = None,
        oracle_text: Optional[str] = None,
        image_url: Optional[str] = None,
        small_image_url: Optional[str] = None,
        rarity: Optional[str] = None,
        set_code: Optional[str] = None,
        set_name: Optional[str] = None,
        scryfall_uri: Optional[str] = None,
    ) -> Card:
        """Create a new card with all details from Scryfall."""
        db_card = Card(
            name=name,
            scryfall_id=scryfall_id,
            mana_cost=mana_cost,
            type_line=type_line,
            colors=colors,
            cmc=cmc,
            power=power,
            toughness=toughness,
            oracle_text=oracle_text,
            image_url=image_url,
            small_image_url=small_image_url,
            rarity=rarity,
            set_code=set_code,
            set_name=set_name,
            scryfall_uri=scryfall_uri,
        )
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        return db_card

    def get_card_by_id(db: Session, card_id: int) -> Card | None:
        """Get a card by ID."""
        return db.query(Card).filter(Card.id == card_id).first()

    @staticmethod
    def get_card_by_name(db: Session, name: str) -> Card | None:
        """Get a card by name."""
        return db.query(Card).filter(Card.name == name).first()

    @staticmethod
    def get_card_by_scryfall_id(db: Session, scryfall_id: str) -> Card | None:
        """Get a card by Scryfall ID."""
        return db.query(Card).filter(Card.scryfall_id == scryfall_id).first()

    @staticmethod
    def get_all_cards(db: Session, skip: int = 0, limit: int = 100) -> list[Card]:
        """Get all cards with pagination."""
        return db.query(Card).offset(skip).limit(limit).all()

    @staticmethod
    def update_card(db: Session, card_id: int, card_update: CardCreate) -> Card | None:
        """Update a card."""
        db_card = CardService.get_card_by_id(db, card_id)
        if db_card:
            db_card.name = card_update.name
            db_card.scryfall_id = card_update.scryfall_id
            db.commit()
            db.refresh(db_card)
        return db_card

    @staticmethod
    def update_cached_data(db: Session, card_id: int, cached_data: str) -> Card | None:
        """Update cached Scryfall data for a card."""
        db_card = CardService.get_card_by_id(db, card_id)
        if db_card:
            db_card.cached_data = cached_data
            db.commit()
            db.refresh(db_card)
        return db_card

    @staticmethod
    def delete_card(db: Session, card_id: int) -> bool:
        """Delete a card."""
        db_card = CardService.get_card_by_id(db, card_id)
        if db_card:
            db.delete(db_card)
            db.commit()
            return True
        return False

    @staticmethod
    def search_cards(db: Session, query: str, limit: int = 20) -> list[Card]:
        """Search for cards by name."""
        return db.query(Card).filter(Card.name.ilike(f"%{query}%")).limit(limit).all()
