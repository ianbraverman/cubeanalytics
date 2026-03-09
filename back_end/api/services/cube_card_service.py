from sqlalchemy.orm import Session, joinedload
from api.models import CubeCard
from api.schemas import CubeCardCreate

class CubeCardService:
    """Service class for cube-card relationship operations."""

    @staticmethod
    def add_card_to_cube(db: Session, cube_id: int, cube_card: CubeCardCreate) -> CubeCard:
        """Add a card to a cube."""
        db_cube_card = CubeCard(
            cube_id=cube_id,
            card_id=cube_card.card_id,
            quantity=cube_card.quantity
        )
        db.add(db_cube_card)
        db.commit()
        db.refresh(db_cube_card)
        # Eager load the card relationship
        db.refresh(db_cube_card, ['card'])
        return db_cube_card

    @staticmethod
    def get_cube_card_by_id(db: Session, cube_card_id: int) -> CubeCard | None:
        """Get a cube-card relationship by ID."""
        return db.query(CubeCard).filter(CubeCard.id == cube_card_id).first()

    @staticmethod
    def get_cards_in_cube(db: Session, cube_id: int) -> list[CubeCard]:
        """Get all cards in a cube with eager-loaded card relationship."""
        return db.query(CubeCard).options(joinedload(CubeCard.card)).filter(CubeCard.cube_id == cube_id).all()

    @staticmethod
    def remove_card_from_cube(db: Session, cube_id: int, card_id: int) -> bool:
        """Remove a card from a cube."""
        db_cube_card = db.query(CubeCard).filter(
            CubeCard.cube_id == cube_id,
            CubeCard.card_id == card_id
        ).first()
        
        if db_cube_card:
            db.delete(db_cube_card)
            db.commit()
            return True
        
        return False

    @staticmethod
    def update_card_quantity(db: Session, cube_id: int, card_id: int, quantity: int) -> CubeCard | None:
        """Update the quantity of a card in a cube."""
        db_cube_card = db.query(CubeCard).filter(
            CubeCard.cube_id == cube_id,
            CubeCard.card_id == card_id
        ).first()
        
        if db_cube_card:
            db_cube_card.quantity = quantity
            db.commit()
            db.refresh(db_cube_card)
        
        return db_cube_card

    @staticmethod
    def delete_all_cards_from_cube(db: Session, cube_id: int) -> int:
        """Delete all cards from a cube. Returns the number of cards deleted."""
        cube_cards = db.query(CubeCard).filter(CubeCard.cube_id == cube_id).all()
        count = len(cube_cards)
        for cube_card in cube_cards:
            db.delete(cube_card)
        db.commit()
        return count

    @staticmethod
    def get_cube_size(db: Session, cube_id: int) -> int:
        """Get the total number of cards in a cube."""
        cube_cards = CubeCardService.get_cards_in_cube(db, cube_id)
        return sum(cc.quantity for cc in cube_cards)
