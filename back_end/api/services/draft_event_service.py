import json
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from api.models import DraftEvent, DraftParticipant
from api.schemas import DraftEventCreate, DraftEventUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DraftEventService:
    """Service class for draft event-related operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_draft_event(db: Session, event: DraftEventCreate) -> DraftEvent:
        hashed_password = DraftEventService.hash_password(event.password)
        db_event = DraftEvent(
            cube_id=event.cube_id,
            password_hash=hashed_password,
            name=event.name,
            num_players=event.num_players or 0,
            status="active",
            event_type=event.event_type or "casual",
            num_rounds=event.num_rounds,
            best_of=event.best_of or 1,
        )
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event

    @staticmethod
    def get_draft_event_by_id(db: Session, event_id: int) -> DraftEvent | None:
        return (
            db.query(DraftEvent)
            .options(
                joinedload(DraftEvent.user_decks),
                joinedload(DraftEvent.participants).joinedload(DraftParticipant.user),
            )
            .filter(DraftEvent.id == event_id)
            .first()
        )

    @staticmethod
    def get_draft_events_by_cube(db: Session, cube_id: int) -> list[DraftEvent]:
        return (
            db.query(DraftEvent)
            .options(
                joinedload(DraftEvent.user_decks),
                joinedload(DraftEvent.participants).joinedload(DraftParticipant.user),
            )
            .filter(DraftEvent.cube_id == cube_id)
            .order_by(DraftEvent.created_at.desc())
            .all()
        )

    @staticmethod
    def update_draft_event(db: Session, event_id: int, update: DraftEventUpdate) -> DraftEvent | None:
        event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
        if not event:
            return None
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        db.commit()
        return DraftEventService.get_draft_event_by_id(db, event_id)

    @staticmethod
    def verify_event_password(db: Session, event_id: int, password: str) -> bool:
        event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
        if event:
            return DraftEventService.verify_password(password, event.password_hash)
        return False

    @staticmethod
    def delete_draft_event(db: Session, event_id: int) -> bool:
        db_event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
        if db_event:
            db.delete(db_event)
            db.commit()
            return True
        return False
