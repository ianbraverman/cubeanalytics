"""
Cube statistics service.

All stat methods accept a cube_id and return plain dicts ready for JSON
serialization.  No heavy ORM relationships are loaded — we favour targeted
queries + Python-side aggregation for simplicity and performance at typical
cube sizes (< 10 000 draft decks).
"""
import json
from collections import defaultdict
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models import (
    Card,
    CardFeedback,
    CubeCard,
    DraftEvent,
    PostDraftFeedback,
    UserDeck,
)

_COLOR_ORDER = "WUBRG"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ids(text: Optional[str]) -> list[int]:
    if not text:
        return []
    try:
        return [int(x) for x in json.loads(text)]
    except Exception:
        return []


def _win_rate(wins: int, losses: int) -> Optional[float]:
    total = wins + losses
    return round(wins / total, 3) if total > 0 else None


# ---------------------------------------------------------------------------
# CubeStatsService
# ---------------------------------------------------------------------------

class CubeStatsService:

    # ── shared query helpers ─────────────────────────────────────────────────

    @staticmethod
    def _event_ids(db: Session, cube_id: int) -> list[int]:
        rows = db.query(DraftEvent.id).filter(DraftEvent.cube_id == cube_id).all()
        return [r.id for r in rows]

    @staticmethod
    def _cube_decks(db: Session, cube_id: int) -> list[UserDeck]:
        event_ids = CubeStatsService._event_ids(db, cube_id)
        if not event_ids:
            return []
        return db.query(UserDeck).filter(UserDeck.draft_event_id.in_(event_ids)).all()

    # ── Card performance ─────────────────────────────────────────────────────

    @staticmethod
    def get_card_stats(db: Session, cube_id: int) -> list[dict]:
        """
        Per-card performance for every card currently in the cube.

        Returns a list sorted by times_maindecked desc, then card name.
        Key fields per entry:
          card_id, card_name, colors, cmc, type_line,
          times_maindecked, times_in_pool, times_in_sideboard,
          times_hate_drafted_or_cut (in pool but never played/sided),
          times_in_winning_deck, total_wins_with, total_losses_with,
          win_rate, inclusion_rate,
          avg_feedback_rating, feedback_count,
          times_standout, times_underperformer
        """
        cube_card_rows = (
            db.query(CubeCard, Card)
            .join(Card, CubeCard.card_id == Card.id)
            .filter(CubeCard.cube_id == cube_id, CubeCard.removed_at.is_(None))
            .all()
        )
        if not cube_card_rows:
            return []
        card_map: dict[int, Card] = {cc.card_id: card for cc, card in cube_card_rows}

        event_ids = CubeStatsService._event_ids(db, cube_id)

        # CardFeedback ratings
        cf_ratings: dict[int, list[int]] = defaultdict(list)
        if event_ids:
            for cf in db.query(CardFeedback).filter(
                CardFeedback.draft_event_id.in_(event_ids)
            ).all():
                cf_ratings[cf.card_id].append(cf.rating)

        # PostDraftFeedback nominations
        standout_counts: dict[int, int] = defaultdict(int)
        underperformer_counts: dict[int, int] = defaultdict(int)
        if event_ids:
            for pdf in db.query(PostDraftFeedback).filter(
                PostDraftFeedback.draft_event_id.in_(event_ids)
            ).all():
                for cid in _parse_ids(pdf.standout_card_ids):
                    standout_counts[cid] += 1
                for cid in _parse_ids(pdf.underperformer_card_ids):
                    underperformer_counts[cid] += 1

        # Per-deck card aggregation
        times_maindecked: dict[int, int] = defaultdict(int)
        times_in_pool: dict[int, int] = defaultdict(int)
        times_in_sideboard: dict[int, int] = defaultdict(int)
        times_in_winning_deck: dict[int, int] = defaultdict(int)
        total_wins_with: dict[int, int] = defaultdict(int)
        total_losses_with: dict[int, int] = defaultdict(int)

        for deck in CubeStatsService._cube_decks(db, cube_id):
            maindeck = set(_parse_ids(deck.deck_cards))
            pool = set(_parse_ids(deck.full_pool_cards))
            sideboard = set(_parse_ids(deck.sideboard_cards))
            wins = deck.wins or 0
            losses = deck.losses or 0

            for card_id in card_map:
                if card_id in pool:
                    times_in_pool[card_id] += 1
                if card_id in maindeck:
                    times_maindecked[card_id] += 1
                    total_wins_with[card_id] += wins
                    total_losses_with[card_id] += losses
                    if wins > losses:
                        times_in_winning_deck[card_id] += 1
                if card_id in sideboard:
                    times_in_sideboard[card_id] += 1

        results = []
        for card_id, card in card_map.items():
            maindecked = times_maindecked[card_id]
            in_pool = times_in_pool[card_id]
            in_sb = times_in_sideboard[card_id]
            wins_w = total_wins_with[card_id]
            losses_w = total_losses_with[card_id]
            # Cards that were drafted (in pool) but never played or sided
            hate_cut = max(0, in_pool - maindecked - in_sb)
            ratings = cf_ratings.get(card_id, [])

            results.append({
                "card_id": card_id,
                "card_name": card.name,
                "image_url": card.small_image_url or card.image_url,
                "colors": card.colors or [],
                "cmc": card.cmc,
                "type_line": card.type_line,
                "times_maindecked": maindecked,
                "times_in_pool": in_pool,
                "times_in_sideboard": in_sb,
                "times_hate_drafted_or_cut": hate_cut,
                "times_in_winning_deck": times_in_winning_deck[card_id],
                "total_wins_with": wins_w,
                "total_losses_with": losses_w,
                "win_rate": _win_rate(wins_w, losses_w),
                "inclusion_rate": round(maindecked / in_pool, 3) if in_pool > 0 else None,
                "avg_feedback_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "feedback_count": len(ratings),
                "times_standout": standout_counts.get(card_id, 0),
                "times_underperformer": underperformer_counts.get(card_id, 0),
            })

        results.sort(key=lambda x: (-x["times_maindecked"], x["card_name"]))
        return results

    # ── Archetype performance ────────────────────────────────────────────────

    @staticmethod
    def get_archetype_stats(db: Session, cube_id: int) -> dict:
        """
        Win rates grouped by macro archetype and specific archetype detail.

        Returns {
          macro_archetypes: [{name, count, total_wins, total_losses, win_rate}],
          detail_archetypes: [...],
          head_to_head: [{archetype_a, archetype_b, a_wins, b_wins, matches}]
        }
        """
        decks = CubeStatsService._cube_decks(db, cube_id)

        macro: dict[str, dict] = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
        detail: dict[str, dict] = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})

        # Deck id → archetype for head-to-head
        deck_archetype: dict[int, str] = {}

        for deck in decks:
            wins = deck.wins or 0
            losses = deck.losses or 0
            if deck.archetype:
                mac = deck.archetype.lower()
                macro[mac]["count"] += 1
                macro[mac]["wins"] += wins
                macro[mac]["losses"] += losses
                deck_archetype[deck.id] = mac
            if deck.archetype_detail:
                det = deck.archetype_detail.lower()
                detail[det]["count"] += 1
                detail[det]["wins"] += wins
                detail[det]["losses"] += losses

        def _format(d: dict) -> list[dict]:
            rows = [
                {
                    "name": k,
                    "count": v["count"],
                    "total_wins": v["wins"],
                    "total_losses": v["losses"],
                    "win_rate": _win_rate(v["wins"], v["losses"]),
                }
                for k, v in d.items()
            ]
            rows.sort(key=lambda x: -x["count"])
            return rows

        # Head-to-head archetype matchups from DraftPairing data
        from api.models import DraftRound, DraftPairing

        event_ids = CubeStatsService._event_ids(db, cube_id)
        h2h: dict[tuple[str, str], dict] = defaultdict(lambda: {"a_wins": 0, "b_wins": 0, "matches": 0})

        if event_ids and deck_archetype:
            # Build deck_id → deck map
            deck_by_id = {d.id: d for d in decks}
            round_ids = [
                r.id for r in db.query(DraftRound.id)
                .filter(DraftRound.draft_event_id.in_(event_ids)).all()
            ]
            if round_ids:
                pairings = db.query(DraftPairing).filter(
                    DraftPairing.round_id.in_(round_ids),
                    DraftPairing.status == "complete",
                ).all()
                for p in pairings:
                    arch_a = deck_archetype.get(p.player1_deck_id)
                    arch_b = deck_archetype.get(p.player2_deck_id)
                    if arch_a and arch_b and arch_a != arch_b:
                        key = tuple(sorted([arch_a, arch_b]))
                        h2h[key]["matches"] += 1
                        if p.winner_user_id == p.player1_user_id:
                            if key[0] == arch_a:
                                h2h[key]["a_wins"] += 1
                            else:
                                h2h[key]["b_wins"] += 1
                        elif p.winner_user_id == p.player2_user_id:
                            if key[0] == arch_b:
                                h2h[key]["a_wins"] += 1
                            else:
                                h2h[key]["b_wins"] += 1

        h2h_list = [
            {
                "archetype_a": k[0],
                "archetype_b": k[1],
                "a_wins": v["a_wins"],
                "b_wins": v["b_wins"],
                "matches": v["matches"],
            }
            for k, v in h2h.items()
        ]
        h2h_list.sort(key=lambda x: -x["matches"])

        return {
            "macro_archetypes": _format(macro),
            "detail_archetypes": _format(detail),
            "head_to_head": h2h_list,
        }

    # ── Color combination performance ────────────────────────────────────────

    @staticmethod
    def get_color_stats(db: Session, cube_id: int) -> dict:
        """
        Win rates and representation by color identity.

        Returns {
          color_pairs: [{color_identity, count, total_wins, total_losses, win_rate}],
          color_representation: {W: 0.6, U: 0.4, ...}  # % of decks containing each color
        }
        """
        decks = CubeStatsService._cube_decks(db, cube_id)
        total = len(decks)

        color_agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
        color_presence: dict[str, int] = defaultdict(int)

        for deck in decks:
            identity = deck.color_identity or "C"
            color_agg[identity]["count"] += 1
            color_agg[identity]["wins"] += deck.wins or 0
            color_agg[identity]["losses"] += deck.losses or 0
            for c in identity:
                if c in _COLOR_ORDER:
                    color_presence[c] += 1

        color_pairs = [
            {
                "color_identity": k,
                "count": v["count"],
                "total_wins": v["wins"],
                "total_losses": v["losses"],
                "win_rate": _win_rate(v["wins"], v["losses"]),
            }
            for k, v in color_agg.items()
        ]
        color_pairs.sort(key=lambda x: -x["count"])

        color_repr = {
            c: round(color_presence[c] / total, 3) if total > 0 else 0.0
            for c in _COLOR_ORDER
        }

        return {"color_pairs": color_pairs, "color_representation": color_repr}

    # ── Card synergy / co-occurrence ─────────────────────────────────────────

    @staticmethod
    def get_synergy_stats(db: Session, cube_id: int, min_co_occurrences: int = 3) -> list[dict]:
        """
        Card pairs that frequently appear together in winning decks.

        Returns [{card_a_id, card_a_name, card_b_id, card_b_name,
                  co_occurrences, co_occur_wins, co_occur_losses, win_rate}]
        sorted by co_occurrences desc.

        Only pairs with at least min_co_occurrences appearances are returned.
        """
        from itertools import combinations

        decks = CubeStatsService._cube_decks(db, cube_id)

        pair_wins: dict[tuple[int, int], int] = defaultdict(int)
        pair_losses: dict[tuple[int, int], int] = defaultdict(int)
        pair_count: dict[tuple[int, int], int] = defaultdict(int)

        for deck in decks:
            ids = sorted(set(_parse_ids(deck.deck_cards)))
            wins = deck.wins or 0
            losses = deck.losses or 0
            for a, b in combinations(ids, 2):
                key = (a, b)
                pair_count[key] += 1
                pair_wins[key] += wins
                pair_losses[key] += losses

        # Filter by threshold
        qualifying = {k: v for k, v in pair_count.items() if v >= min_co_occurrences}
        if not qualifying:
            return []

        # Fetch card names in one query
        all_ids = set()
        for a, b in qualifying:
            all_ids.add(a)
            all_ids.add(b)
        card_names = {
            c.id: c.name
            for c in db.query(Card.id, Card.name).filter(Card.id.in_(all_ids)).all()
        }

        results = [
            {
                "card_a_id": a,
                "card_a_name": card_names.get(a, "Unknown"),
                "card_b_id": b,
                "card_b_name": card_names.get(b, "Unknown"),
                "co_occurrences": pair_count[(a, b)],
                "co_occur_wins": pair_wins[(a, b)],
                "co_occur_losses": pair_losses[(a, b)],
                "win_rate": _win_rate(pair_wins[(a, b)], pair_losses[(a, b)]),
            }
            for a, b in qualifying
        ]
        results.sort(key=lambda x: -x["co_occurrences"])
        return results

    # ── Meta health ──────────────────────────────────────────────────────────

    @staticmethod
    def get_meta_health(db: Session, cube_id: int) -> dict:
        """
        Aggregate cube meta health snapshot.

        Returns {
          total_drafts, total_decks,
          color_representation: {W,U,B,R,G: float},
          archetype_distribution: {archetype: count},
          avg_cmc_winning_decks, avg_cmc_losing_decks,
          dominant_archetype (archetype > 40% of tagged decks, or null),
          color_diversity_index (distinct color identities / total decks),
          distinct_color_identities,
          returning_player_rate  (players in >= 2 events / total unique players)
        }
        """
        decks = CubeStatsService._cube_decks(db, cube_id)
        if not decks:
            return {
                "total_drafts": 0,
                "total_decks": 0,
                "color_representation": {c: 0.0 for c in _COLOR_ORDER},
                "archetype_distribution": {},
                "avg_cmc_winning_decks": None,
                "avg_cmc_losing_decks": None,
                "dominant_archetype": None,
                "color_diversity_index": None,
                "distinct_color_identities": 0,
                "returning_player_rate": None,
            }

        event_ids_seen = set(d.draft_event_id for d in decks)
        total_drafts = len(event_ids_seen)
        total_decks = len(decks)

        # Color representation
        color_presence: dict[str, int] = defaultdict(int)
        for deck in decks:
            for c in (deck.color_identity or ""):
                if c in _COLOR_ORDER:
                    color_presence[c] += 1
        color_repr = {
            c: round(color_presence[c] / total_decks, 3)
            for c in _COLOR_ORDER
        }

        # Archetype distribution
        archetype_counts: dict[str, int] = defaultdict(int)
        for deck in decks:
            if deck.archetype:
                archetype_counts[deck.archetype.lower()] += 1
        archetype_dist = dict(sorted(archetype_counts.items(), key=lambda x: -x[1]))

        # Dominant archetype (> 40% among tagged decks)
        tagged = sum(archetype_counts.values())
        dominant = None
        if tagged > 0:
            for arch, cnt in archetype_counts.items():
                if cnt / tagged > 0.40:
                    dominant = arch
                    break

        # Avg CMC of winning vs losing decks
        all_card_ids: set[int] = set()
        for deck in decks:
            all_card_ids.update(_parse_ids(deck.deck_cards))
        card_cmc: dict[int, float] = {}
        if all_card_ids:
            card_cmc = {
                c.id: c.cmc
                for c in db.query(Card.id, Card.cmc).filter(Card.id.in_(all_card_ids)).all()
                if c.cmc is not None
            }

        winning_cmcs: list[float] = []
        losing_cmcs: list[float] = []
        for deck in decks:
            ids = _parse_ids(deck.deck_cards)
            cmcs = [card_cmc[i] for i in ids if i in card_cmc]
            if not cmcs:
                continue
            avg = sum(cmcs) / len(cmcs)
            wins = deck.wins or 0
            losses = deck.losses or 0
            if wins > losses:
                winning_cmcs.append(avg)
            elif losses > wins:
                losing_cmcs.append(avg)

        avg_cmc_win = round(sum(winning_cmcs) / len(winning_cmcs), 3) if winning_cmcs else None
        avg_cmc_lose = round(sum(losing_cmcs) / len(losing_cmcs), 3) if losing_cmcs else None

        # Color diversity
        distinct_identities = len(set(d.color_identity for d in decks if d.color_identity))
        diversity_index = round(distinct_identities / total_decks, 3) if total_decks > 0 else None

        # Returning player rate
        from collections import Counter
        player_event_counts: Counter = Counter(
            d.user_id for d in decks if d.user_id is not None
        )
        unique_players = len(player_event_counts)
        returning = sum(1 for cnt in player_event_counts.values() if cnt >= 2)
        returning_rate = round(returning / unique_players, 3) if unique_players > 0 else None

        return {
            "total_drafts": total_drafts,
            "total_decks": total_decks,
            "color_representation": color_repr,
            "archetype_distribution": archetype_dist,
            "avg_cmc_winning_decks": avg_cmc_win,
            "avg_cmc_losing_decks": avg_cmc_lose,
            "dominant_archetype": dominant,
            "color_diversity_index": diversity_index,
            "distinct_color_identities": distinct_identities,
            "returning_player_rate": returning_rate,
        }

    # ── Feedback aggregation ─────────────────────────────────────────────────

    @staticmethod
    def get_feedback_stats(db: Session, cube_id: int) -> list[dict]:
        """
        Per-card feedback summary across all drafts for a cube.

        Returns [{card_id, card_name, avg_rating, total_ratings,
                  times_standout, times_underperformer, flagged_problematic}]
        sorted by total signal (ratings + nominations) desc.

        A card is flagged_problematic when avg_rating <= 2.5 or it has
        more underperformer nominations than standout nominations.
        """
        event_ids = CubeStatsService._event_ids(db, cube_id)
        if not event_ids:
            return []

        cf_data: dict[int, dict] = defaultdict(lambda: {"ratings": [], "comments": []})
        for cf in db.query(CardFeedback).filter(
            CardFeedback.draft_event_id.in_(event_ids)
        ).all():
            cf_data[cf.card_id]["ratings"].append(cf.rating)
            if cf.comment:
                cf_data[cf.card_id]["comments"].append(cf.comment)

        standout_counts: dict[int, int] = defaultdict(int)
        underperformer_counts: dict[int, int] = defaultdict(int)
        for pdf in db.query(PostDraftFeedback).filter(
            PostDraftFeedback.draft_event_id.in_(event_ids)
        ).all():
            for cid in _parse_ids(pdf.standout_card_ids):
                standout_counts[cid] += 1
            for cid in _parse_ids(pdf.underperformer_card_ids):
                underperformer_counts[cid] += 1

        all_card_ids = (
            set(cf_data.keys()) | set(standout_counts.keys()) | set(underperformer_counts.keys())
        )
        card_name_map = {
            c.id: c.name
            for c in db.query(Card.id, Card.name).filter(Card.id.in_(all_card_ids)).all()
        }

        results = []
        for card_id in all_card_ids:
            ratings = cf_data[card_id]["ratings"]
            avg_r = round(sum(ratings) / len(ratings), 2) if ratings else None
            standouts = standout_counts.get(card_id, 0)
            underperformers = underperformer_counts.get(card_id, 0)
            flagged = (avg_r is not None and avg_r <= 2.5) or (underperformers > standouts and underperformers > 0)
            results.append({
                "card_id": card_id,
                "card_name": card_name_map.get(card_id, "Unknown"),
                "avg_rating": avg_r,
                "total_ratings": len(ratings),
                "times_standout": standouts,
                "times_underperformer": underperformers,
                "flagged_problematic": flagged,
            })

        results.sort(
            key=lambda x: -(x["total_ratings"] + x["times_standout"] + x["times_underperformer"])
        )
        return results

    # ── Player stats ─────────────────────────────────────────────────────────

    @staticmethod
    def get_player_stats(
        db: Session, user_id: int, cube_id: Optional[int] = None
    ) -> dict:
        """
        Comprehensive performance stats for a player, optionally scoped to a cube.

        Returns per-cube breakdown, archetype / color win rates, most-drafted
        cards, best cards by win rate, head-to-head records against opponents,
        a full recent draft history, and the player's best-ever deck.
        """
        from api.models import Cube, User, DraftRound, DraftPairing

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        query = db.query(UserDeck).filter(UserDeck.user_id == user_id)
        if cube_id is not None:
            scoped_event_ids = CubeStatsService._event_ids(db, cube_id)
            query = query.filter(UserDeck.draft_event_id.in_(scoped_event_ids))
        decks = query.all()

        _empty = {
            "user_id": user_id,
            "username": user.username,
            "cube_id": cube_id,
            "total_drafts": 0,
            "total_decks": 0,
            "total_wins": 0,
            "total_losses": 0,
            "overall_win_rate": None,
            "cubes_played": [],
            "archetype_breakdown": [],
            "color_breakdown": [],
            "most_drafted_cards": [],
            "best_cards": [],
            "head_to_head": [],
            "recent_drafts": [],
            "best_deck": None,
        }
        if not decks:
            return _empty

        # ── Lookup tables ────────────────────────────────────────────────────
        event_id_set = {d.draft_event_id for d in decks}
        events = db.query(DraftEvent).filter(DraftEvent.id.in_(event_id_set)).all()
        event_map = {e.id: e for e in events}

        cube_id_set = {e.cube_id for e in events}
        cubes = db.query(Cube).filter(Cube.id.in_(cube_id_set)).all()
        cube_map = {c.id: c for c in cubes}

        # ── Totals ───────────────────────────────────────────────────────────
        total_wins = sum(d.wins or 0 for d in decks)
        total_losses = sum(d.losses or 0 for d in decks)
        total_drafts = len(event_id_set)

        # ── Per-cube breakdown ────────────────────────────────────────────────
        cube_agg: dict[int, dict] = defaultdict(lambda: {"drafts": 0, "wins": 0, "losses": 0})
        for deck in decks:
            ev = event_map.get(deck.draft_event_id)
            if ev:
                cube_agg[ev.cube_id]["drafts"] += 1
                cube_agg[ev.cube_id]["wins"] += deck.wins or 0
                cube_agg[ev.cube_id]["losses"] += deck.losses or 0

        cubes_played = sorted(
            [
                {
                    "cube_id": cid,
                    "cube_name": cube_map[cid].name if cid in cube_map else "Unknown",
                    "draft_count": agg["drafts"],
                    "total_wins": agg["wins"],
                    "total_losses": agg["losses"],
                    "win_rate": _win_rate(agg["wins"], agg["losses"]),
                }
                for cid, agg in cube_agg.items()
            ],
            key=lambda x: -x["draft_count"],
        )

        # ── Archetype breakdown (with W/L) ────────────────────────────────────
        arch_agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
        for deck in decks:
            if deck.archetype:
                key = deck.archetype.lower()
                arch_agg[key]["count"] += 1
                arch_agg[key]["wins"] += deck.wins or 0
                arch_agg[key]["losses"] += deck.losses or 0

        archetype_breakdown = sorted(
            [
                {
                    "archetype": k,
                    "count": v["count"],
                    "wins": v["wins"],
                    "losses": v["losses"],
                    "win_rate": _win_rate(v["wins"], v["losses"]),
                }
                for k, v in arch_agg.items()
            ],
            key=lambda x: -x["count"],
        )

        # ── Color identity breakdown (with W/L) ───────────────────────────────
        color_agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0})
        for deck in decks:
            if deck.color_identity:
                color_agg[deck.color_identity]["count"] += 1
                color_agg[deck.color_identity]["wins"] += deck.wins or 0
                color_agg[deck.color_identity]["losses"] += deck.losses or 0

        color_breakdown = sorted(
            [
                {
                    "color_identity": k,
                    "count": v["count"],
                    "wins": v["wins"],
                    "losses": v["losses"],
                    "win_rate": _win_rate(v["wins"], v["losses"]),
                }
                for k, v in color_agg.items()
            ],
            key=lambda x: -x["count"],
        )

        # ── Per-card stats ────────────────────────────────────────────────────
        card_wins_map: dict[int, int] = defaultdict(int)
        card_losses_map: dict[int, int] = defaultdict(int)
        card_count_map: dict[int, int] = defaultdict(int)
        for deck in decks:
            wins = deck.wins or 0
            losses = deck.losses or 0
            for cid in set(_parse_ids(deck.deck_cards)):
                card_count_map[cid] += 1
                card_wins_map[cid] += wins
                card_losses_map[cid] += losses

        all_card_ids = list(card_count_map.keys())
        card_name_map: dict[int, str] = {}
        if all_card_ids:
            card_name_map = {
                c.id: c.name
                for c in db.query(Card.id, Card.name).filter(Card.id.in_(all_card_ids)).all()
            }

        card_entries = [
            {
                "card_id": cid,
                "card_name": card_name_map.get(cid, "Unknown"),
                "times_played": card_count_map[cid],
                "wins_with": card_wins_map[cid],
                "losses_with": card_losses_map[cid],
                "win_rate": _win_rate(card_wins_map[cid], card_losses_map[cid]),
            }
            for cid in all_card_ids
        ]
        most_drafted_cards = sorted(card_entries, key=lambda x: -x["times_played"])[:12]
        best_cards = sorted(
            [c for c in card_entries if c["times_played"] >= 2 and c["win_rate"] is not None],
            key=lambda x: (-(x["win_rate"] or 0), -x["times_played"]),
        )[:10]

        # ── Head-to-head ──────────────────────────────────────────────────────
        all_event_ids = list(event_id_set)
        round_ids = [
            r.id
            for r in db.query(DraftRound.id)
            .filter(DraftRound.draft_event_id.in_(all_event_ids))
            .all()
        ]
        h2h: dict[int, dict] = defaultdict(lambda: {"wins": 0, "losses": 0, "matches": 0})
        if round_ids:
            pairings = (
                db.query(DraftPairing)
                .filter(
                    DraftPairing.round_id.in_(round_ids),
                    DraftPairing.status == "complete",
                    or_(
                        DraftPairing.player1_user_id == user_id,
                        DraftPairing.player2_user_id == user_id,
                    ),
                )
                .all()
            )
            for p in pairings:
                opp_id = (
                    p.player2_user_id
                    if p.player1_user_id == user_id
                    else p.player1_user_id
                )
                if opp_id is None:
                    continue  # bye
                h2h[opp_id]["matches"] += 1
                if p.winner_user_id == user_id:
                    h2h[opp_id]["wins"] += 1
                elif p.winner_user_id == opp_id:
                    h2h[opp_id]["losses"] += 1

        opp_ids = list(h2h.keys())
        opp_name_map: dict[int, str] = {}
        if opp_ids:
            opp_name_map = {
                u.id: u.username
                for u in db.query(User.id, User.username).filter(User.id.in_(opp_ids)).all()
            }

        head_to_head = sorted(
            [
                {
                    "opponent_user_id": opp_id,
                    "opponent_username": opp_name_map.get(opp_id, f"Player {opp_id}"),
                    "wins": v["wins"],
                    "losses": v["losses"],
                    "matches": v["matches"],
                    "win_rate": _win_rate(v["wins"], v["losses"]),
                }
                for opp_id, v in h2h.items()
            ],
            key=lambda x: -x["matches"],
        )

        # ── Recent drafts (last 20) ───────────────────────────────────────────
        def _event_date(deck: UserDeck):
            ev = event_map.get(deck.draft_event_id)
            return ev.created_at if ev and ev.created_at else None

        recent = sorted(
            decks,
            key=lambda d: _event_date(d) or __import__("datetime").datetime.min,
            reverse=True,
        )[:20]

        recent_drafts = []
        for deck in recent:
            ev = event_map.get(deck.draft_event_id)
            cube_obj = cube_map.get(ev.cube_id) if ev else None
            recent_drafts.append(
                {
                    "draft_event_id": deck.draft_event_id,
                    "deck_id": deck.id,
                    "event_name": ev.name if ev else f"Draft #{deck.draft_event_id}",
                    "cube_id": ev.cube_id if ev else None,
                    "cube_name": cube_obj.name if cube_obj else "Unknown",
                    "deck_name": deck.deck_name,
                    "archetype": deck.archetype,
                    "archetype_detail": deck.archetype_detail,
                    "color_identity": deck.color_identity,
                    "wins": deck.wins or 0,
                    "losses": deck.losses or 0,
                    "record": deck.record or f"{deck.wins or 0}-{deck.losses or 0}",
                    "date": ev.created_at.isoformat() if ev and ev.created_at else None,
                }
            )

        # ── Best deck ─────────────────────────────────────────────────────────
        best_deck = None
        best_wr = -1.0
        for deck in decks:
            games = (deck.wins or 0) + (deck.losses or 0)
            if games == 0:
                continue
            wr = (deck.wins or 0) / games
            is_better = wr > best_wr or (
                wr == best_wr and (deck.wins or 0) > (best_deck["wins"] if best_deck else -1)
            )
            if is_better:
                best_wr = wr
                ev = event_map.get(deck.draft_event_id)
                cube_obj = cube_map.get(ev.cube_id) if ev else None
                best_deck = {
                    "deck_id": deck.id,
                    "deck_name": deck.deck_name,
                    "record": deck.record or f"{deck.wins or 0}-{deck.losses or 0}",
                    "wins": deck.wins or 0,
                    "losses": deck.losses or 0,
                    "archetype": deck.archetype,
                    "archetype_detail": deck.archetype_detail,
                    "color_identity": deck.color_identity,
                    "draft_event_id": deck.draft_event_id,
                    "event_name": ev.name if ev else None,
                    "cube_name": cube_obj.name if cube_obj else None,
                    "ai_description": deck.ai_description,
                }

        return {
            "user_id": user_id,
            "username": user.username,
            "cube_id": cube_id,
            "total_drafts": total_drafts,
            "total_decks": len(decks),
            "total_wins": total_wins,
            "total_losses": total_losses,
            "overall_win_rate": _win_rate(total_wins, total_losses),
            "cubes_played": cubes_played,
            "archetype_breakdown": archetype_breakdown,
            "color_breakdown": color_breakdown,
            "most_drafted_cards": most_drafted_cards,
            "best_cards": best_cards,
            "head_to_head": head_to_head,
            "recent_drafts": recent_drafts,
            "best_deck": best_deck,
        }
