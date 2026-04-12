"""Statistics endpoints for cube owners and players."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.services import CubeStatsService, UserDeckService, AIService, CardService
from api.schemas import UserDeckUpdate
from api.models import UserDeck
from database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Cube-scoped statistics ────────────────────────────────────────────────────

@router.get("/cubes/{cube_id}/cards")
async def cube_card_stats(cube_id: int, db: Session = Depends(get_db)):
    """
    Per-card performance for every active card in a cube.

    Returns win rate, inclusion rate, hate-draft/cut rate, pool appearances,
    and aggregated player feedback ratings and nominations.
    """
    return CubeStatsService.get_card_stats(db, cube_id)


@router.get("/cubes/{cube_id}/archetypes")
async def cube_archetype_stats(cube_id: int, db: Session = Depends(get_db)):
    """
    Win rates by macro archetype (aggro/midrange/control/combo/other),
    by specific archetype detail (red aggro, aristocrats, etc.),
    and head-to-head matchup records between archetypes.
    """
    return CubeStatsService.get_archetype_stats(db, cube_id)


@router.get("/cubes/{cube_id}/colors")
async def cube_color_stats(cube_id: int, db: Session = Depends(get_db)):
    """
    Win rates by color identity (WR, UB, WUBRG, C, etc.) and per-color
    representation rates across all decks.
    """
    return CubeStatsService.get_color_stats(db, cube_id)


@router.get("/cubes/{cube_id}/synergies")
async def cube_synergy_stats(
    cube_id: int,
    min_co_occurrences: int = Query(3, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Card pairs that frequently appear together in decks for this cube.

    Includes co-occurrence count and win rate for decks containing both cards.
    Raise min_co_occurrences to narrow results to more established packages.
    """
    return CubeStatsService.get_synergy_stats(db, cube_id, min_co_occurrences)


@router.get("/cubes/{cube_id}/meta")
async def cube_meta_health(cube_id: int, db: Session = Depends(get_db)):
    """
    Aggregate meta health snapshot: color balance, archetype diversity,
    avg CMC of winning vs losing decks, dominant archetype detection,
    and returning player rate.
    """
    return CubeStatsService.get_meta_health(db, cube_id)


@router.get("/cubes/{cube_id}/feedback")
async def cube_feedback_stats(cube_id: int, db: Session = Depends(get_db)):
    """
    Per-card feedback aggregation: average ratings, standout/underperformer
    nomination counts, and automatic problem-card flagging.
    """
    return CubeStatsService.get_feedback_stats(db, cube_id)


# ── Player statistics ─────────────────────────────────────────────────────────

@router.get("/players/{user_id}")
async def player_stats(
    user_id: int,
    cube_id: Optional[int] = Query(None, description="Scope stats to a specific cube"),
    db: Session = Depends(get_db),
):
    """
    Performance stats for a player: win rate, favourite archetype and colour
    identity, archetype/colour breakdowns, best-performing deck.

    Pass cube_id to scope the results to a single cube.
    """
    return CubeStatsService.get_player_stats(db, user_id, cube_id)


# ── Deck archetype tagging ────────────────────────────────────────────────────

@router.post("/decks/{deck_id}/generate-tags")
async def generate_deck_tags(deck_id: int, db: Session = Depends(get_db)):
    """
    Use AI to classify a deck's archetype and populate the archetype /
    archetype_detail fields.  Also recomputes color_identity from deck cards.

    Idempotent — safe to call multiple times; will overwrite previous tags.
    """
    deck = db.query(UserDeck).filter(UserDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    card_ids = UserDeckService._deserialize(deck.deck_cards)
    card_names = []
    for cid in card_ids:
        card = CardService.get_card_by_id(db, cid)
        if card:
            card_names.append(card.name)

    # Recompute color identity
    color_identity = UserDeckService.compute_color_identity(db, card_ids)

    # AI archetype tagging
    tags = {"archetype": "", "archetype_detail": ""}
    if card_names:
        try:
            tags = AIService.generate_deck_tags(card_names)
        except Exception as exc:
            logger.warning("generate_deck_tags failed for deck %s: %s", deck_id, exc)

    update = UserDeckUpdate(
        archetype=tags["archetype"] or None,
        archetype_detail=tags["archetype_detail"] or None,
        color_identity=color_identity,
    )
    updated = UserDeckService.update_user_deck(db, deck_id, update)
    return {
        "deck_id": deck_id,
        "archetype": updated.archetype,
        "archetype_detail": updated.archetype_detail,
        "color_identity": updated.color_identity,
    }


@router.post("/cubes/{cube_id}/generate-all-tags")
async def generate_all_deck_tags(cube_id: int, db: Session = Depends(get_db)):
    """
    Bulk-tag all decks in a cube that don't yet have an archetype set.

    Returns a summary of how many decks were tagged vs skipped.
    Safe to re-run; skips decks that already have an archetype unless
    force=true is passed.
    """
    from api.models import DraftEvent

    event_ids = [
        e.id for e in db.query(DraftEvent.id).filter(DraftEvent.cube_id == cube_id).all()
    ]
    if not event_ids:
        return {"tagged": 0, "skipped": 0, "errors": 0}

    decks = db.query(UserDeck).filter(
        UserDeck.draft_event_id.in_(event_ids),
        UserDeck.archetype.is_(None),
    ).all()

    tagged = 0
    errors = 0
    for deck in decks:
        card_ids = UserDeckService._deserialize(deck.deck_cards)
        card_names = []
        for cid in card_ids:
            card = CardService.get_card_by_id(db, cid)
            if card:
                card_names.append(card.name)

        color_identity = UserDeckService.compute_color_identity(db, card_ids)
        tags = {"archetype": "", "archetype_detail": ""}
        if card_names:
            try:
                tags = AIService.generate_deck_tags(card_names)
            except Exception:
                errors += 1
                continue

        UserDeckService.update_user_deck(
            db,
            deck.id,
            UserDeckUpdate(
                archetype=tags["archetype"] or None,
                archetype_detail=tags["archetype_detail"] or None,
                color_identity=color_identity,
            ),
        )
        tagged += 1

    return {"tagged": tagged, "skipped": 0, "errors": errors}
