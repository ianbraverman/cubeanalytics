from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class CubeCard(Base):
    __tablename__ = "cube_cards"

    id = Column(Integer, primary_key=True, index=True)
    cube_id = Column(Integer, ForeignKey("cubes.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)            # soft-delete: when card left the cube

    # Relationships
    cube = relationship("Cube", back_populates="cube_cards")
    card = relationship("Card", back_populates="cube_cards")
