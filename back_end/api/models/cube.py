from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Cube(Base):
    __tablename__ = "cubes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Gameplay settings (defaults for cube events)
    life_total = Column(Integer, default=20, nullable=False)          # starting life per player
    pack_count = Column(Integer, default=3, nullable=False)           # number of packs per drafter
    pack_size = Column(Integer, default=15, nullable=False)           # cards per pack
    draft_rules = Column(Text, nullable=True)                        # freeform draft rules / notes
    gameplay_rules = Column(Text, nullable=True)                     # freeform gameplay rules / notes
    cubecobra_link = Column(String, nullable=True)                   # optional CubeCobra page URL

    # Relationships
    owner = relationship("User", back_populates="cubes")
    draft_events = relationship("DraftEvent", back_populates="cube", cascade="all, delete")
    cube_cards = relationship("CubeCard", back_populates="cube", cascade="all, delete")
