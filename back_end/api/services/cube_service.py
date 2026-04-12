from sqlalchemy.orm import Session
from api.models import Cube
from api.schemas import CubeCreate, CubeSettingsUpdate

class CubeService:
    """Service class for cube-related operations."""

    @staticmethod
    def create_cube(db: Session, cube: CubeCreate, owner_id: int) -> Cube:
        """Create a new cube in the database."""
        db_cube = Cube(
            name=cube.name,
            description=cube.description,
            cubecobra_link=cube.cubecobra_link,
            owner_id=owner_id
        )
        db.add(db_cube)
        db.commit()
        db.refresh(db_cube)
        return db_cube

    @staticmethod
    def get_cube_by_id(db: Session, cube_id: int) -> Cube | None:
        """Get a cube by ID."""
        return db.query(Cube).filter(Cube.id == cube_id).first()

    @staticmethod
    def get_cubes_by_owner(db: Session, owner_id: int) -> list[Cube]:
        """Get all cubes owned by a user."""
        return db.query(Cube).filter(Cube.owner_id == owner_id).all()

    @staticmethod
    def get_all_cubes(db: Session) -> list[Cube]:
        """Get all cubes in the database."""
        return db.query(Cube).all()

    @staticmethod
    def update_cube(db: Session, cube_id: int, cube_update: CubeCreate) -> Cube | None:
        """Update a cube."""
        db_cube = CubeService.get_cube_by_id(db, cube_id)
        if db_cube:
            db_cube.name = cube_update.name
            db_cube.description = cube_update.description
            db_cube.cubecobra_link = cube_update.cubecobra_link
            db.commit()
            db.refresh(db_cube)
        return db_cube

    @staticmethod
    def update_cube_settings(db: Session, cube_id: int, settings: CubeSettingsUpdate) -> Cube | None:
        """Update gameplay/pack settings for a cube."""
        db_cube = CubeService.get_cube_by_id(db, cube_id)
        if not db_cube:
            return None
        for field, value in settings.model_dump(exclude_unset=True).items():
            setattr(db_cube, field, value)
        db.commit()
        db.refresh(db_cube)
        return db_cube

    @staticmethod
    def delete_cube(db: Session, cube_id: int) -> bool:
        """Delete a cube."""
        db_cube = CubeService.get_cube_by_id(db, cube_id)
        if db_cube:
            db.delete(db_cube)
            db.commit()
            return True
        return False
