"""Draft event endpoints — full CRUD + AI generation + hosted event management."""
import json
import os
import random
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from api.schemas import (
    DraftEventCreate, DraftEventUpdate, DraftEventResponse,
    UserDeckCreate, UserDeckUpdate,
    DraftSeatResponse, DraftRoundResponse, DraftPairingResponse,
    SubmitMatchResult, RoundFeedbackCreate, RoundFeedbackResponse,
    PostDraftFeedbackCreate, PostDraftFeedbackResponse,
)
from api.services import DraftEventService, UserDeckService, AIService, CardService, CubeCardService
from api.models import DraftEvent, DraftParticipant, User, DraftSeat, DraftRound, DraftPairing, RoundFeedback, PostDraftFeedback
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("uploads/deck_photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── helpers ──────────────────────────────────────────────────────────────────

def _deck_response(deck):
    return UserDeckService.deck_to_dict(deck)


def _event_response(event, include_decks=False):
    base = {
        "id": event.id,
        "cube_id": event.cube_id,
        "name": event.name,
        "status": event.status,
        "num_players": event.num_players,
        "ai_summary": event.ai_summary,
        "event_type": event.event_type or "casual",
        "num_rounds": event.num_rounds,
        "best_of": event.best_of or 1,
        "current_round": event.current_round or 0,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "participants": [
            {"user_id": p.user_id, "username": p.user.username, "joined_at": p.joined_at}
            for p in event.participants
        ] if hasattr(event, 'participants') and event.participants is not None else [],
    }
    if include_decks:
        base["user_decks"] = [_deck_response(d) for d in event.user_decks]
    return base


def _get_cube_card_name_candidates(db: Session, event_id: int) -> list[str]:
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        return []

    cube_cards = CubeCardService.get_cards_in_cube(db, event.cube_id)
    names: list[str] = []
    seen: set[str] = set()
    for cube_card in cube_cards:
        card_name = cube_card.card.name if cube_card.card else None
        if not card_name:
            continue
        key = card_name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(card_name)
    return names


# ── Draft Event CRUD ──────────────────────────────────────────────────────────

@router.post("/")
async def create_draft_event(
    event: DraftEventCreate,
    created_by_user_id: int = Query(None),
    db: Session = Depends(get_db),
):
    new_event = DraftEventService.create_draft_event(db, event)
    if created_by_user_id:
        db.add(DraftParticipant(draft_event_id=new_event.id, user_id=created_by_user_id))
        db.commit()
    return _event_response(DraftEventService.get_draft_event_by_id(db, new_event.id))


@router.get("/cube/{cube_id}")
async def get_cube_draft_events(cube_id: int, db: Session = Depends(get_db)):
    events = DraftEventService.get_draft_events_by_cube(db, cube_id)
    return [_event_response(e, include_decks=True) for e in events]


@router.get("/user/{user_id}")
async def get_user_draft_events(user_id: int, db: Session = Depends(get_db)):
    """Return all draft events the user has participated in, with their own deck info."""
    from api.models import UserDeck, Cube
    participations = (
        db.query(DraftParticipant)
        .filter(DraftParticipant.user_id == user_id)
        .all()
    )
    result = []
    for p in participations:
        event = p.draft_event
        if not event:
            continue
        cube = db.query(Cube).filter(Cube.id == event.cube_id).first()
        my_deck = db.query(UserDeck).filter(
            UserDeck.draft_event_id == event.id,
            UserDeck.user_id == user_id,
        ).first()
        result.append({
            **_event_response(event, include_decks=False),
            "cube_name": cube.name if cube else None,
            "joined_at": p.joined_at.isoformat() if p.joined_at else None,
            "my_deck": {
                "id": my_deck.id,
                "player_name": my_deck.player_name,
                "deck_name": my_deck.deck_name,
                "wins": my_deck.wins,
                "losses": my_deck.losses,
                "record": my_deck.record,
                "ai_description": my_deck.ai_description,
            } if my_deck else None,
        })
    # Sort: active drafts first, then by date desc
    result.sort(key=lambda x: (x["status"] == "completed", x["created_at"]))
    return result


@router.get("/{event_id}")
async def get_draft_event(event_id: int, db: Session = Depends(get_db)):
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    return _event_response(event, include_decks=True)


@router.patch("/{event_id}")
async def update_draft_event(event_id: int, update: DraftEventUpdate, db: Session = Depends(get_db)):
    event = DraftEventService.update_draft_event(db, event_id, update)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    return _event_response(event, include_decks=True)


@router.patch("/{event_id}/password")
async def change_draft_password(
    event_id: int,
    new_password: str = Query(..., min_length=6),
    db: Session = Depends(get_db),
):
    event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    event.password_hash = DraftEventService.hash_password(new_password)
    db.commit()
    return {"message": "Password updated"}


@router.delete("/{event_id}")
async def delete_draft_event(event_id: int, db: Session = Depends(get_db)):
    success = DraftEventService.delete_draft_event(db, event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft event not found")
    return {"message": "Draft event deleted"}


@router.post("/{event_id}/verify-password")
async def verify_event_password(
    event_id: int,
    password: str = Query(...),
    user_id: int = Query(None, description="If provided, record this user as a participant"),
    db: Session = Depends(get_db),
):
    is_valid = DraftEventService.verify_event_password(db, event_id, password)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid password")
    # Record participation if user_id provided
    if user_id:
        existing = db.query(DraftParticipant).filter_by(draft_event_id=event_id, user_id=user_id).first()
        if not existing:
            db.add(DraftParticipant(draft_event_id=event_id, user_id=user_id))
            db.commit()
    return {"message": "Password verified"}


# ── Decks ─────────────────────────────────────────────────────────────────────

@router.get("/{event_id}/decks")
async def get_decks(event_id: int, db: Session = Depends(get_db)):
    decks = UserDeckService.get_decks_for_event(db, event_id)
    return [_deck_response(d) for d in decks]


@router.post("/{event_id}/decks")
async def create_deck(event_id: int, deck: UserDeckCreate, db: Session = Depends(get_db)):
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    deck.draft_event_id = event_id
    user_id = deck.user_id  # None for guest decks entered by the cube owner on behalf of a player
    new_deck = UserDeckService.create_user_deck(db, deck, user_id=user_id)
    return _deck_response(new_deck)


@router.patch("/{event_id}/decks/{deck_id}")
async def update_deck(event_id: int, deck_id: int, update: UserDeckUpdate, db: Session = Depends(get_db)):
    deck = UserDeckService.update_user_deck(db, deck_id, update)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return _deck_response(deck)


@router.delete("/{event_id}/decks/{deck_id}")
async def delete_deck(event_id: int, deck_id: int, db: Session = Depends(get_db)):
    success = UserDeckService.delete_user_deck(db, deck_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deck not found")
    return {"message": "Deck deleted"}


# ── Photo upload ──────────────────────────────────────────────────────────────

@router.post("/{event_id}/decks/{deck_id}/photo")
async def upload_deck_photo(
    event_id: int,
    deck_id: int,
    file: UploadFile = File(...),
    analyze: bool = Query(False, description="Run AI card recognition on the photo"),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    save_path = UPLOAD_DIR / filename
    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    photo_url = f"/uploads/deck_photos/{filename}"
    deck = UserDeckService.update_user_deck(db, deck_id, UserDeckUpdate(deck_photo_url=photo_url))
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    result = {"deck_photo_url": photo_url}

    if analyze:
        try:
            image_bytes = save_path.read_bytes()
            mime = file.content_type or "image/jpeg"
            candidate_names = _get_cube_card_name_candidates(db, event_id)
            identified = AIService.identify_cards_from_photo(
                image_bytes,
                mime,
                candidate_card_names=candidate_names,
            )
            result["identified_cards"] = identified
            if not identified:
                result["ai_error"] = "No card names could be identified from this photo. Try a clearer, closer image with less glare."
        except Exception as e:
            result["ai_error"] = str(e)

    return result


# ── Dual-photo analysis ─────────────────────────────────────────────────────────

@router.post("/{event_id}/decks/{deck_id}/analyze-photos")
async def analyze_deck_photos(
    event_id: int,
    deck_id: int,
    deck_file: UploadFile = File(...),
    pool_file: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
):
    """Upload deck photo and optionally a full-pool photo. AI identifies both, diffs to produce sideboard."""
    deck = UserDeckService.get_user_deck_by_id(db, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Save deck photo
    ext1 = Path(deck_file.filename).suffix if deck_file.filename else ".jpg"
    deck_filename = f"{uuid.uuid4()}{ext1}"
    deck_path = UPLOAD_DIR / deck_filename
    with deck_path.open("wb") as f:
        shutil.copyfileobj(deck_file.file, f)
    deck_photo_url = f"/uploads/deck_photos/{deck_filename}"

    # Save pool photo (optional)
    pool_photo_url: str | None = None
    pool_path: Path | None = None
    if pool_file is not None:
        ext2 = Path(pool_file.filename).suffix if pool_file.filename else ".jpg"
        pool_filename = f"{uuid.uuid4()}{ext2}"
        pool_path = UPLOAD_DIR / pool_filename
        with pool_path.open("wb") as f:
            shutil.copyfileobj(pool_file.file, f)
        pool_photo_url = f"/uploads/deck_photos/{pool_filename}"

    # Persist photo URLs immediately
    UserDeckService.update_user_deck(
        db, deck_id,
        UserDeckUpdate(deck_photo_url=deck_photo_url, pool_photo_url=pool_photo_url)
    )

    result: dict = {
        "deck_photo_url": deck_photo_url,
        "pool_photo_url": pool_photo_url,
        "deck_identified": [],
        "pool_identified": [],
        "sideboard_identified": [],
    }

    try:
        deck_bytes = deck_path.read_bytes()
        deck_mime = deck_file.content_type or "image/jpeg"
        candidate_names = _get_cube_card_name_candidates(db, event_id)

        deck_error: str | None = None
        pool_error: str | None = None

        try:
            deck_identified = AIService.identify_cards_from_photo(
                deck_bytes,
                deck_mime,
                candidate_card_names=candidate_names,
            )
        except Exception as exc:
            deck_identified = []
            deck_error = str(exc)

        pool_identified: list[str] = []
        if pool_path is not None:
            pool_mime = pool_file.content_type or "image/jpeg"  # type: ignore[union-attr]
            try:
                pool_identified = AIService.identify_cards_from_photo(
                    pool_path.read_bytes(),
                    pool_mime,
                    candidate_card_names=candidate_names,
                )
            except Exception as exc:
                pool_error = str(exc)

        # Sideboard = cards in full pool that are NOT in the deck
        deck_set = {n.lower() for n in deck_identified}
        # Only compute sideboard when pool analysis actually returned results
        if pool_identified:
            sideboard_identified = [n for n in pool_identified if n.lower() not in deck_set]
        else:
            sideboard_identified = []

        result["deck_identified"] = deck_identified
        result["pool_identified"] = pool_identified
        result["sideboard_identified"] = sideboard_identified
        if deck_error:
            result["deck_photo_error"] = f"Deck photo analysis failed: {deck_error}"
        if pool_error:
            result["pool_photo_error"] = f"Pool photo analysis failed: {pool_error}"
        if not deck_identified and not pool_identified:
            result["ai_error"] = "No card names could be identified from either photo. Try clearer, closer photos with card titles fully visible."
        else:
            # Persist identified names as card IDs on the user deck where possible
            def _names_to_ids(names: list[str]) -> list[int]:
                ids: list[int] = []
                for nm in names:
                    card = CardService.get_card_by_name(db, nm)
                    if card:
                        ids.append(card.id)
                    else:
                        # try exact-case-insensitive match fallback
                        found = CardService.search_cards(db, nm, limit=10)
                        match = None
                        for c in found:
                            if c.name.strip().lower() == nm.strip().lower():
                                match = c
                                break
                        if match:
                            ids.append(match.id)
                        else:
                            # not found: log and skip
                            logger.warning("Identified card name not found in DB: %s", nm)
                return ids

            # Only include a field in the update when we actually have data for it.
            # Using `or None` would pass None explicitly and clear existing DB data,
            # so we build the payload selectively.
            update_kwargs: dict = {}
            if deck_identified:
                update_kwargs["deck_cards"] = _names_to_ids(deck_identified)
            if pool_identified:
                pool_ids = _names_to_ids(pool_identified)
                update_kwargs["full_pool_cards"] = pool_ids
            if sideboard_identified:
                update_kwargs["sideboard_cards"] = _names_to_ids(sideboard_identified)

            if update_kwargs:
                try:
                    UserDeckService.update_user_deck(
                        db, deck_id,
                        UserDeckUpdate(**update_kwargs)
                    )
                except Exception:
                    logger.exception("Failed to persist identified cards for deck_id=%s", deck_id)
    except Exception as e:
        result["ai_error"] = str(e)

    return result


# ── AI generation ──────────────────────────────────────────────────────────────

@router.post("/{event_id}/decks/{deck_id}/ai-description")
async def generate_deck_description(event_id: int, deck_id: int, db: Session = Depends(get_db)):
    deck = UserDeckService.get_user_deck_by_id(db, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    card_ids = UserDeckService._deserialize(deck.deck_cards)
    card_names = []
    for cid in card_ids:
        card = CardService.get_card_by_id(db, cid)
        if card:
            card_names.append(card.name)

    try:
        description = AIService.generate_deck_description(
            player_name=deck.player_name,
            deck_name=deck.deck_name,
            card_names=card_names,
            record=deck.record,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    UserDeckService.update_user_deck(db, deck_id, UserDeckUpdate(ai_description=description))
    return {"ai_description": description}


@router.post("/{event_id}/ai-summary")
async def generate_draft_summary(event_id: int, db: Session = Depends(get_db)):
    from api.services.cube_service import CubeService
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")

    cube = CubeService.get_cube_by_id(db, event.cube_id)

    # ── Build rich deck data — card names + auto-generate missing descriptions ──
    deck_data = []
    for d in event.user_decks:
        card_ids = UserDeckService._deserialize(d.deck_cards)
        card_names: list[str] = []
        for cid in card_ids:
            card = CardService.get_card_by_id(db, cid)
            if card:
                card_names.append(card.name)

        # Auto-generate deck description if missing
        description = d.ai_description
        if not description and card_names:
            try:
                description = AIService.generate_deck_description(
                    player_name=d.player_name,
                    deck_name=d.deck_name,
                    card_names=card_names,
                    record=d.record,
                )
                UserDeckService.update_user_deck(
                    db, d.id, UserDeckUpdate(ai_description=description)
                )
                logger.info("Auto-generated description for deck_id=%s", d.id)
            except Exception:
                logger.warning("Could not auto-generate description for deck_id=%s", d.id)

        deck_data.append({
            "player_name": d.player_name,
            "deck_name": d.deck_name,
            "record": d.record,
            "ai_description": description or "",
            "card_names": card_names,
        })

    # ── Load round/pairing data for matchup context ──
    rounds_data: list[dict] = []
    try:
        db_rounds = db.query(DraftRound).filter(DraftRound.draft_event_id == event_id).order_by(DraftRound.round_number).all()
        for r in db_rounds:
            pairings_info = []
            for p in r.pairings:
                p1_name = p.player1.username if p.player1 else None
                p2_name = p.player2.username if p.player2 else "BYE"
                winner_name = None
                if p.winner_user_id:
                    if p.winner_user_id == p.player1_user_id:
                        winner_name = p1_name
                    elif p.player2 and p.winner_user_id == p.player2_user_id:
                        winner_name = p2_name
                pairings_info.append({
                    "p1_name": p1_name,
                    "p2_name": p2_name,
                    "p1_wins": p.player1_wins or 0,
                    "p2_wins": p.player2_wins or 0,
                    "winner_name": winner_name,
                })
            rounds_data.append({"round_num": r.round_number, "pairings": pairings_info})
    except Exception:
        logger.warning("Could not load round data for event_id=%s", event_id)

    # ── Load post-draft feedback ──────────────────────────────────────────────
    feedback_data: list[dict] = []
    try:
        post_fb = db.query(PostDraftFeedback).filter(PostDraftFeedback.draft_event_id == event_id).all()
        for fb in post_fb:
            # Use saved player_name first, then look up via user_id in decks
            player_name = fb.player_name
            if not player_name and fb.user_id:
                player_name = next(
                    (d.player_name for d in event.user_decks if d.user_id == fb.user_id),
                    None,
                )
            if not player_name:
                player_name = f"Player {fb.user_id}" if fb.user_id else "Anonymous"
            feedback_data.append({
                "player_name": player_name,
                "rating": fb.overall_rating,
                "thoughts": fb.overall_thoughts,
                "recommendations": fb.recommendations_for_owner,
            })
    except Exception:
        logger.warning("Could not load feedback for event_id=%s", event_id)

    try:
        summary = AIService.generate_draft_summary(
            draft_name=event.name,
            cube_name=cube.name if cube else None,
            decks=deck_data,
            rounds=rounds_data or None,
            feedback=feedback_data or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    DraftEventService.update_draft_event(db, event_id, DraftEventUpdate(ai_summary=summary))
    return {"ai_summary": summary}


# ── Hosted event: seating ─────────────────────────────────────────────────────

@router.post("/{event_id}/start")
async def start_event(event_id: int, db: Session = Depends(get_db)):
    """Assign random seat numbers to all current participants and advance status."""
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    if event.event_type != "hosted":
        raise HTTPException(status_code=400, detail="Only hosted events support seating")

    participants = event.participants
    if not participants:
        raise HTTPException(status_code=400, detail="No participants have joined yet")

    # Delete any existing seat assignments, then reassign
    db.query(DraftSeat).filter(DraftSeat.draft_event_id == event_id).delete()

    shuffled = list(participants)
    random.shuffle(shuffled)
    for i, p in enumerate(shuffled, start=1):
        db.add(DraftSeat(draft_event_id=event_id, user_id=p.user_id, seat_number=i))

    raw_event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
    raw_event.status = "seating_assigned"
    db.commit()

    seats = db.query(DraftSeat).filter(DraftSeat.draft_event_id == event_id).all()
    return {
        "message": "Seating assigned",
        "seats": [
            {"user_id": s.user_id, "username": s.user.username, "seat_number": s.seat_number}
            for s in sorted(seats, key=lambda s: s.seat_number)
        ],
    }


@router.get("/{event_id}/seating")
async def get_seating(event_id: int, db: Session = Depends(get_db)):
    """Return current seat assignments."""
    seats = (
        db.query(DraftSeat)
        .filter(DraftSeat.draft_event_id == event_id)
        .order_by(DraftSeat.seat_number)
        .all()
    )
    return [
        {"user_id": s.user_id, "username": s.user.username, "seat_number": s.seat_number}
        for s in seats
    ]


@router.post("/{event_id}/advance")
async def advance_event_status(
    event_id: int,
    new_status: str | None = Query(None, description="Override target status. If omitted, auto-advances to next phase."),
    db: Session = Depends(get_db),
):
    """Advance the event to the next phase."""
    _next_status = {
        "active": "seating_assigned",
        "seating_assigned": "drafting",
        "drafting": "deck_submission",
        "deck_submission": "in_rounds",
        "in_rounds": "completed",
    }
    event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")
    if new_status:
        allowed = {"seating_assigned", "drafting", "deck_submission", "in_rounds", "completed"}
        if new_status not in allowed:
            raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed}")
        target = new_status
    else:
        current = event.status or "active"
        target = _next_status.get(current)
        if not target:
            raise HTTPException(status_code=400, detail=f"No next phase defined for status '{current}'")
    event.status = target
    db.commit()
    return {"status": target}


# ── Hosted event: rounds & pairings ─────────────────────────────────────────

def _swiss_pairings(players_ranked: list[dict]) -> list[tuple]:
    """Simple Swiss: sort by wins desc, pair adjacent, last gets bye if odd."""
    paired: list[tuple] = []
    pool = list(players_ranked)
    while len(pool) >= 2:
        p1 = pool.pop(0)
        # find first eligible opponent (haven't played each other) or just the next one
        p2 = pool.pop(0)
        paired.append((p1, p2))
    if pool:
        paired.append((pool[0], None))  # bye
    return paired


@router.post("/{event_id}/next-round")
async def start_next_round(event_id: int, db: Session = Depends(get_db)):
    """Generate pairings for the next round using simple Swiss standings."""
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")

    # Verify previous round (if any) is complete
    if event.current_round > 0:
        last_round = (
            db.query(DraftRound)
            .filter(DraftRound.draft_event_id == event_id, DraftRound.round_number == event.current_round)
            .first()
        )
        if last_round and last_round.status != "complete":
            raise HTTPException(status_code=400, detail="Current round is not yet complete")

    next_round_num = (event.current_round or 0) + 1
    if event.num_rounds and next_round_num > event.num_rounds:
        raise HTTPException(status_code=400, detail="All rounds are already complete")

    # Build standings: {user_id: wins}
    decks = event.user_decks
    wins_by_user: dict[int, int] = {}
    deck_by_user: dict[int, int] = {}
    for d in decks:
        wins_by_user[d.user_id] = d.wins or 0
        deck_by_user[d.user_id] = d.id

    participants = event.participants
    players_ranked = sorted(
        [{"user_id": p.user_id, "username": p.user.username, "wins": wins_by_user.get(p.user_id, 0)}
         for p in participants],
        key=lambda x: -x["wins"],
    )

    # Create round record
    new_round = DraftRound(draft_event_id=event_id, round_number=next_round_num)
    db.add(new_round)
    db.flush()

    pairs = _swiss_pairings(players_ranked)
    for p1, p2 in pairs:
        pairing = DraftPairing(
            round_id=new_round.id,
            player1_user_id=p1["user_id"],
            player2_user_id=p2["user_id"] if p2 else None,
            player1_deck_id=deck_by_user.get(p1["user_id"]),
            player2_deck_id=deck_by_user.get(p2["user_id"]) if p2 else None,
            # byes are auto-won by p1
            player1_wins=1 if p2 is None else 0,
            winner_user_id=p1["user_id"] if p2 is None else None,
            player1_confirmed="yes" if p2 is None else "no",
            player2_confirmed="yes" if p2 is None else "no",
            status="complete" if p2 is None else "pending",
        )
        db.add(pairing)

    raw_event = db.query(DraftEvent).filter(DraftEvent.id == event_id).first()
    raw_event.current_round = next_round_num
    raw_event.status = "in_rounds"
    db.commit()
    db.refresh(new_round)

    return _round_response(new_round)


@router.get("/{event_id}/rounds/{round_num}")
async def get_round(event_id: int, round_num: int, db: Session = Depends(get_db)):
    """Get pairings for a specific round."""
    r = db.query(DraftRound).filter(
        DraftRound.draft_event_id == event_id,
        DraftRound.round_number == round_num,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Round not found")
    return _round_response(r)


@router.get("/{event_id}/rounds")
async def get_all_rounds(event_id: int, db: Session = Depends(get_db)):
    """Get all rounds for an event."""
    rounds = db.query(DraftRound).filter(DraftRound.draft_event_id == event_id).order_by(DraftRound.round_number).all()
    return [_round_response(r) for r in rounds]


def _round_response(r: DraftRound) -> dict:
    return {
        "id": r.id,
        "round_number": r.round_number,
        "status": r.status,
        "pairings": [_pairing_response(p) for p in r.pairings],
    }


def _pairing_response(p: DraftPairing) -> dict:
    return {
        "id": p.id,
        "player1_user_id": p.player1_user_id,
        "player2_user_id": p.player2_user_id,
        "player1_name": p.player1.username if p.player1 else None,
        "player2_name": p.player2.username if p.player2 else "BYE",
        "player1_deck_id": p.player1_deck_id,
        "player2_deck_id": p.player2_deck_id,
        "player1_wins": p.player1_wins,
        "player2_wins": p.player2_wins,
        "winner_user_id": p.winner_user_id,
        "player1_confirmed": p.player1_confirmed,
        "player2_confirmed": p.player2_confirmed,
        "status": p.status,
    }


@router.patch("/{event_id}/pairings/{pairing_id}/result")
async def submit_match_result(
    event_id: int,
    pairing_id: int,
    body: SubmitMatchResult,
    user_id: int | None = Query(None, description="The user submitting the result"),
    db: Session = Depends(get_db),
):
    """Submit or update match result. Both players must confirm for status to become 'complete'."""
    pairing = db.query(DraftPairing).filter(DraftPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing not found")

    # Resolve submitting user: body takes priority, then query param
    submitting = body.submitting_user_id or user_id
    is_p1 = pairing.player1_user_id == submitting if submitting else False
    is_p2 = pairing.player2_user_id == submitting if submitting else False

    # If we can't identify the player (no user_id provided), still allow
    # result entry but mark both sides confirmed (host/fallback mode)
    if submitting and not is_p1 and not is_p2:
        raise HTTPException(status_code=403, detail="You are not a player in this pairing")

    # Capture existing values before any overwrite so we can detect conflicts
    existing_p1_wins = pairing.player1_wins
    existing_p2_wins = pairing.player2_wins

    # Conflict detection: if the other player already confirmed, check whether
    # this submission matches what was stored. If not, reset both.
    if is_p2 and pairing.player1_confirmed == "yes":
        if body.player1_wins != existing_p1_wins or body.player2_wins != existing_p2_wins:
            pairing.player1_confirmed = "no"
            pairing.player2_confirmed = "no"
            db.commit()
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Result conflict: your opponent submitted "
                    f"{existing_p1_wins}–{existing_p2_wins} but you submitted "
                    f"{body.player1_wins}–{body.player2_wins}. "
                    "Both players must re-submit agreeing results."
                ),
            )
    if is_p1 and pairing.player2_confirmed == "yes":
        if body.player1_wins != existing_p1_wins or body.player2_wins != existing_p2_wins:
            pairing.player1_confirmed = "no"
            pairing.player2_confirmed = "no"
            db.commit()
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Result conflict: your opponent submitted "
                    f"{existing_p1_wins}–{existing_p2_wins} but you submitted "
                    f"{body.player1_wins}–{body.player2_wins}. "
                    "Both players must re-submit agreeing results."
                ),
            )

    pairing.player1_wins = body.player1_wins
    pairing.player2_wins = body.player2_wins

    if is_p1:
        pairing.player1_confirmed = "yes"
    elif is_p2:
        pairing.player2_confirmed = "yes"
    else:
        # No user identity — treat as host entry, confirm both sides
        pairing.player1_confirmed = "yes"
        pairing.player2_confirmed = "yes"

    # Determine winner once both confirm
    if pairing.player1_confirmed == "yes" and pairing.player2_confirmed == "yes":
        if body.player1_wins > body.player2_wins:
            pairing.winner_user_id = pairing.player1_user_id
        elif body.player2_wins > body.player1_wins:
            pairing.winner_user_id = pairing.player2_user_id
        else:
            pairing.winner_user_id = None  # draw

        pairing.status = "complete"

        # Update deck win/loss records
        _update_deck_record(db, pairing, event_id)

        # Check if the whole round is done
        _maybe_complete_round(db, pairing.round_id)

    db.commit()
    return _pairing_response(pairing)


def _update_deck_record(db: Session, pairing: DraftPairing, event_id: int):
    """Adjust wins/losses on user deck rows after a match is confirmed."""
    from api.models import UserDeck as UD
    p1_wins = pairing.player1_wins
    p2_wins = pairing.player2_wins
    if pairing.player1_deck_id:
        d = db.query(UD).filter(UD.id == pairing.player1_deck_id).first()
        if d:
            if p1_wins > p2_wins:
                d.wins = (d.wins or 0) + 1
            elif p2_wins > p1_wins:
                d.losses = (d.losses or 0) + 1
    if pairing.player2_deck_id:
        d = db.query(UD).filter(UD.id == pairing.player2_deck_id).first()
        if d:
            if p2_wins > p1_wins:
                d.wins = (d.wins or 0) + 1
            elif p1_wins > p2_wins:
                d.losses = (d.losses or 0) + 1


def _maybe_complete_round(db: Session, round_id: int):
    """Mark the round complete if every pairing is complete."""
    r = db.query(DraftRound).filter(DraftRound.id == round_id).first()
    if r and all(p.status == "complete" for p in r.pairings):
        r.status = "complete"


# ── Hosted event: round feedback ──────────────────────────────────────────────

@router.post("/{event_id}/pairings/{pairing_id}/feedback")
async def submit_round_feedback(
    event_id: int,
    pairing_id: int,
    body: RoundFeedbackCreate,
    db: Session = Depends(get_db),
):
    """Submit round feedback for a pairing (liked/disliked cards + thoughts)."""
    # Upsert: one per user per pairing
    existing = db.query(RoundFeedback).filter(
        RoundFeedback.pairing_id == pairing_id,
        RoundFeedback.user_id == body.user_id,
    ).first()
    fb = existing or RoundFeedback(pairing_id=pairing_id, user_id=body.user_id)
    fb.liked_card_ids = json.dumps(body.liked_card_ids or [])
    fb.disliked_card_ids = json.dumps(body.disliked_card_ids or [])
    fb.liked_notes = body.liked_notes
    fb.disliked_notes = body.disliked_notes
    fb.general_thoughts = body.general_thoughts
    if not existing:
        db.add(fb)
    db.commit()
    db.refresh(fb)
    return _round_feedback_response(fb)


@router.get("/{event_id}/pairings/{pairing_id}/feedback")
async def get_round_feedback(event_id: int, pairing_id: int, db: Session = Depends(get_db)):
    entries = db.query(RoundFeedback).filter(RoundFeedback.pairing_id == pairing_id).all()
    return [_round_feedback_response(f) for f in entries]


def _round_feedback_response(f: RoundFeedback) -> dict:
    def _load(v):
        try:
            return json.loads(v) if v else []
        except Exception:
            return []
    return {
        "id": f.id,
        "pairing_id": f.pairing_id,
        "user_id": f.user_id,
        "liked_card_ids": _load(f.liked_card_ids),
        "disliked_card_ids": _load(f.disliked_card_ids),
        "liked_notes": f.liked_notes,
        "disliked_notes": f.disliked_notes,
        "general_thoughts": f.general_thoughts,
        "created_at": f.created_at,
    }


# ── Hosted event: post-draft feedback ────────────────────────────────────────

@router.post("/{event_id}/post-draft-feedback")
async def submit_post_draft_feedback(
    event_id: int,
    body: PostDraftFeedbackCreate,
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Submit overall post-draft feedback from a player.
    Organizers can omit user_id and supply player_name instead.
    """
    resolved_user_id = body.user_id or user_id
    resolved_player_name = body.player_name

    # Look up existing: prefer match by user_id if provided, else by player_name
    if resolved_user_id:
        existing = db.query(PostDraftFeedback).filter(
            PostDraftFeedback.draft_event_id == event_id,
            PostDraftFeedback.user_id == resolved_user_id,
        ).first()
    elif resolved_player_name:
        existing = db.query(PostDraftFeedback).filter(
            PostDraftFeedback.draft_event_id == event_id,
            PostDraftFeedback.player_name == resolved_player_name,
            PostDraftFeedback.user_id.is_(None),
        ).first()
    else:
        raise HTTPException(status_code=400, detail="Provide user_id or player_name")

    fb = existing or PostDraftFeedback(
        draft_event_id=event_id,
        user_id=resolved_user_id,
        player_name=resolved_player_name,
    )
    fb.overall_rating = body.overall_rating
    fb.overall_thoughts = body.overall_thoughts
    fb.standout_card_ids = json.dumps(body.standout_card_ids or [])
    fb.underperformer_card_ids = json.dumps(body.underperformer_card_ids or [])
    fb.recommendations_for_owner = body.recommendations_for_owner
    fb.cards_to_add = body.cards_to_add
    fb.cards_to_cut = body.cards_to_cut
    if resolved_player_name:
        fb.player_name = resolved_player_name
    if not existing:
        db.add(fb)
    db.commit()
    db.refresh(fb)
    return _post_draft_fb_response(fb)


@router.get("/{event_id}/post-draft-feedback")
async def get_post_draft_feedback(event_id: int, db: Session = Depends(get_db)):
    entries = db.query(PostDraftFeedback).filter(PostDraftFeedback.draft_event_id == event_id).all()
    return [_post_draft_fb_response(f) for f in entries]


def _post_draft_fb_response(f: PostDraftFeedback) -> dict:
    def _load(v):
        try:
            return json.loads(v) if v else []
        except Exception:
            return []
    # Resolve a display name: player_name field → user.username → fallback
    display_name = f.player_name
    if not display_name and hasattr(f, 'user') and f.user:
        display_name = f.user.username
    elif not display_name and f.user_id:
        display_name = f"Player {f.user_id}"
    return {
        "id": f.id,
        "draft_event_id": f.draft_event_id,
        "user_id": f.user_id,
        "player_name": display_name,
        "overall_rating": f.overall_rating,
        "overall_thoughts": f.overall_thoughts,
        "standout_card_ids": _load(f.standout_card_ids),
        "underperformer_card_ids": _load(f.underperformer_card_ids),
        "recommendations_for_owner": f.recommendations_for_owner,
        "cards_to_add": f.cards_to_add,
        "cards_to_cut": f.cards_to_cut,
        "created_at": f.created_at,
    }


# ── Hosted event: full summary ────────────────────────────────────────────────

@router.get("/{event_id}/full-summary")
async def get_full_summary(event_id: int, db: Session = Depends(get_db)):
    """Return a complete event summary for cube owners: decks, rounds, pairings, all feedback."""
    from api.services.cube_service import CubeService
    event = DraftEventService.get_draft_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Draft event not found")

    cube = CubeService.get_cube_by_id(db, event.cube_id)
    rounds = db.query(DraftRound).filter(DraftRound.draft_event_id == event_id).order_by(DraftRound.round_number).all()
    post_fb = db.query(PostDraftFeedback).filter(PostDraftFeedback.draft_event_id == event_id).all()

    # Build card mention tallies across all round feedback
    liked_tally: dict[int, int] = {}
    disliked_tally: dict[int, int] = {}
    for r in rounds:
        for p in r.pairings:
            for fb in p.feedback_entries:
                for cid in json.loads(fb.liked_card_ids or "[]"):
                    liked_tally[cid] = liked_tally.get(cid, 0) + 1
                for cid in json.loads(fb.disliked_card_ids or "[]"):
                    disliked_tally[cid] = disliked_tally.get(cid, 0) + 1

    def _card_name(cid: int) -> str:
        c = CardService.get_card_by_id(db, cid)
        return c.name if c else f"#{cid}"

    return {
        "event": _event_response(event, include_decks=True),
        "cube": {
            "id": cube.id if cube else None,
            "name": cube.name if cube else None,
            "life_total": cube.life_total if cube else 20,
            "pack_count": cube.pack_count if cube else 3,
            "pack_size": cube.pack_size if cube else 15,
            "draft_rules": cube.draft_rules if cube else None,
            "gameplay_rules": cube.gameplay_rules if cube else None,
        },
        "rounds": [_round_response(r) for r in rounds],
        "post_draft_feedback": [_post_draft_fb_response(f) for f in post_fb],
        "card_feedback_summary": {
            "most_liked": sorted(
                [{"card_id": k, "name": _card_name(k), "mentions": v} for k, v in liked_tally.items()],
                key=lambda x: -x["mentions"],
            )[:20],
            "most_disliked": sorted(
                [{"card_id": k, "name": _card_name(k), "mentions": v} for k, v in disliked_tally.items()],
                key=lambda x: -x["mentions"],
            )[:20],
        },
    }
