from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.schemas import CubeCreate, CubeResponse, CubeSettingsUpdate
from api.services import CubeService
from database import SessionLocal

router = APIRouter()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=CubeResponse)
async def create_cube(cube: CubeCreate, owner_id: int, db: Session = Depends(get_db)):
    """Create a new cube."""
    new_cube = CubeService.create_cube(db, cube, owner_id)
    return new_cube

@router.get("/{cube_id}", response_model=CubeResponse)
async def get_cube(cube_id: int, db: Session = Depends(get_db)):
    """Get a cube by ID."""
    cube = CubeService.get_cube_by_id(db, cube_id)
    if not cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    return cube

@router.get("/owner/{owner_id}")
async def get_user_cubes(owner_id: int, db: Session = Depends(get_db)):
    """Get all cubes owned by a user."""
    cubes = CubeService.get_cubes_by_owner(db, owner_id)
    return cubes

@router.get("/")
async def get_all_cubes(db: Session = Depends(get_db)):
    """Get all cubes."""
    cubes = CubeService.get_all_cubes(db)
    return cubes

@router.put("/{cube_id}", response_model=CubeResponse)
async def update_cube(cube_id: int, cube: CubeCreate, db: Session = Depends(get_db)):
    """Update a cube."""
    updated_cube = CubeService.update_cube(db, cube_id, cube)
    if not updated_cube:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    return updated_cube

@router.delete("/{cube_id}")
async def delete_cube(cube_id: int, db: Session = Depends(get_db)):
    """Delete a cube."""
    success = CubeService.delete_cube(db, cube_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    return {"message": "Cube deleted successfully"}

@router.get("/{cube_id}/cards")
async def get_cube_cards(cube_id: int, db: Session = Depends(get_db)):
    """Get the cards in a cube."""
    cards = CubeService.get_cube_cards(db, cube_id)
    if cards is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cube not found"
        )
    return {"cards": cards}

@router.patch("/{cube_id}/settings", response_model=CubeResponse)
async def update_cube_settings(
    cube_id: int,
    settings: CubeSettingsUpdate,
    db: Session = Depends(get_db),
):
    """Update gameplay/pack settings for a cube (life total, pack size, draft rules, etc.)."""
    updated = CubeService.update_cube_settings(db, cube_id, settings)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cube not found")
    return updated
