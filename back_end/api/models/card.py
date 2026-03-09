from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    scryfall_id = Column(String, unique=True, index=True, nullable=False)  # Unique Scryfall ID
    mana_cost = Column(String, nullable=True)  # e.g., "{1}{W}{U}"
    type_line = Column(String, nullable=True)  # e.g., "Creature — Elf Wizard"
    colors = Column(JSON, nullable=True)  # e.g., ["W", "U", "B"]
    cmc = Column(Float, nullable=True)  # Converted mana cost
    power = Column(String, nullable=True)  # e.g., "3" or "*"
    toughness = Column(String, nullable=True)  # e.g., "2" or "*"
    oracle_text = Column(Text, nullable=True)  # Card rules text
    image_url = Column(String, nullable=True)  # Normal-sized image
    small_image_url = Column(String, nullable=True)  # Small image
    rarity = Column(String, nullable=True)  # common, uncommon, rare, mythic
    set_code = Column(String, nullable=True)  # Set abbreviation
    set_name = Column(String, nullable=True)  # Set full name
    scryfall_uri = Column(String, nullable=True)  # Link to Scryfall
    cached_data = Column(Text, nullable=True)  # JSON: optional cache of full Scryfall data
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cube_cards = relationship("CubeCard", back_populates="card")
    feedback = relationship("CardFeedback", back_populates="card")
