"""
AI service for draft analytics.
Uses OpenAI GPT-4o for text generation and GPT-4o vision for deck photo analysis.

Requires OPENAI_API_KEY in your .env file.
"""
import os
import base64
import json
import logging
import re
from io import BytesIO
from difflib import get_close_matches
from typing import Optional
import time

try:
    import google.genai as genai
    _gemini_available = True
except ImportError:
    _gemini_available = False

try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    _openai_available = False

try:
    from PIL import Image
    from PIL import ImageFilter
    from PIL import ImageOps
    from PIL import ImageStat
    _pillow_available = True
except ImportError:
    _pillow_available = False


logger = logging.getLogger(__name__)


def _get_client():
    if not _gemini_available:
        raise RuntimeError("google.genai package not installed. Run: pip install google-genai")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    # google.genai exposes a Client class; instantiate it with the API key.
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception:
        # Fallback: return module if client construction not available
        return genai


class AIService:
    """Handles all OpenAI-powered features for drafts and decks."""

    _REFUSAL_MARKERS = (
        "i'm sorry",
        "i am sorry",
        "i cannot",
        "i can't",
        "unable to",
        "can't assist",
        "cannot assist",
        "can't help",
        "cannot help",
        "cannot display",
        "can't display",
        "unable to transcribe",
    )

    @staticmethod
    def _is_refusal_text(text: str) -> bool:
        check = (text or "").strip().lower()
        if not check:
            return False
        return any(marker in check for marker in AIService._REFUSAL_MARKERS)

    @staticmethod
    def _normalize_card_names(raw: str) -> list[str]:
        if not raw:
            return []

        parsed_names: list[str] = []
        trimmed = raw.strip()

        if trimmed.startswith("["):
            try:
                maybe_json = json.loads(trimmed)
                if isinstance(maybe_json, list):
                    parsed_names.extend([str(item).strip() for item in maybe_json if str(item).strip()])
            except Exception:
                pass

        if not parsed_names:
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            for line in lines:
                cleaned = re.sub(r"^[-*•\d\.)\s]+", "", line).strip()
                if cleaned:
                    parsed_names.append(cleaned)

        if len(parsed_names) == 1 and "," in parsed_names[0]:
            split_names = [name.strip() for name in parsed_names[0].split(",") if name.strip()]
            if len(split_names) > 1:
                parsed_names = split_names

        unique: list[str] = []
        seen: set[str] = set()
        for name in parsed_names:
            if AIService._is_refusal_text(name):
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(name)
        return unique

    @staticmethod
    def _apply_candidate_matching(names: list[str], candidate_card_names: list[str]) -> list[str]:
        if not names or not candidate_card_names:
            return names

        canonical_by_lower = {
            candidate.strip().lower(): candidate.strip()
            for candidate in candidate_card_names
            if candidate and candidate.strip()
        }
        candidate_keys = list(canonical_by_lower.keys())

        matched: list[str] = []
        seen: set[str] = set()
        for raw_name in names:
            key = raw_name.strip().lower()
            canonical = canonical_by_lower.get(key)
            if canonical is None:
                close = get_close_matches(key, candidate_keys, n=1, cutoff=0.72)
                if close:
                    canonical = canonical_by_lower[close[0]]

            if canonical:
                canon_key = canonical.lower()
                if canon_key not in seen:
                    seen.add(canon_key)
                    matched.append(canonical)

        return matched

    @staticmethod
    def _build_prompts(candidates: list[str]) -> list[str]:
        card_list_text = "\n".join(candidates)
        if candidates:
            primary_prompt = (
                "Please identify all Magic: The Gathering cards visible in this image.\n\n"
                "I have provided a list of valid card names below. "
                "Please match the cards you see in the image to card names from this list. "
                "Be as accurate as possible. If you are uncertain about a card, skip it.\n\n"
                "For each card you identify, provide ONLY the exact card name from the list below (one per line).\n\n"
                f"Valid card names:\n{card_list_text}\n\n"
                "List the identified cards:"
            )
            fallback_prompt = (
                "Extract visible MTG card names from this image. "
                "Return ONLY exact names from the provided valid list, one per line. "
                "No explanations or apologies. Skip uncertain cards.\n\n"
                f"Valid card names:\n{card_list_text}\n\n"
                "List the identified cards:"
            )
        else:
            primary_prompt = (
                "Please identify all Magic: The Gathering cards visible in this image.\n\n"
                "For each card you identify, provide ONLY the exact card name (one per line). "
                "If a card title is unreadable, skip it.\n\n"
                "List the identified cards:"
            )
            fallback_prompt = (
                "Extract visible MTG card names from this image. "
                "Return ONLY card names, one per line. No explanations or apologies. "
                "Skip uncertain cards."
            )
        return [primary_prompt, fallback_prompt]

    @staticmethod
    def _identify_from_data_url(
        client,
        image_bytes: bytes,
        mime_type: str,
        candidates: list[str],
    ) -> tuple[list[str], str]:
        prompts = AIService._build_prompts(candidates)
        last_raw = ""


        # prefer the newer SDK usage where we send a PIL Image object alongside the prompt
        vision_model = os.getenv("GEMINI_VISION_MODEL", "gemini-3-flash-preview")

        for prompt in prompts:
            raw = ""
            # client may be a genai.Client instance or the genai module (fallback).
            models = getattr(client, "models", None)
            if models is None and hasattr(client, "Client"):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                models = client.models

            # First try: construct a PIL Image and send as contents list [prompt, image]
            try:
                pil_image = None
                if _pillow_available:
                    with BytesIO(image_bytes) as b:
                        pil_image = Image.open(b).convert("RGB")

                if pil_image is not None:
                    try:
                        response = models.generate_content(model=vision_model, contents=[prompt, pil_image])
                        raw = getattr(response, "text", None) or ""
                        if not raw:
                            cand = getattr(response, "candidates", None) or getattr(response, "output", None)
                            if cand and len(cand) > 0:
                                parts = getattr(cand[0].content, "parts", [])
                                texts = [p.text for p in parts if hasattr(p, "text") and p.text]
                                raw = "\n".join(texts)
                    except Exception:
                        # fall through to legacy inlineData approach below
                        raw = ""
                else:
                    raw = ""
            except Exception:
                raw = ""

            # If the PIL-based call failed or returned nothing, fall back to the inlineData payload
            if not raw:
                try:
                    contents = {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inlineData": {"mimeType": mime_type, "data": image_bytes}},
                        ],
                    }
                    response = models.generate_content(model=vision_model, contents=contents)
                    raw = getattr(response, "text", None) or ""
                    if not raw:
                        try:
                            cand = getattr(response, "candidates", None)
                            if cand and len(cand) > 0:
                                parts = getattr(cand[0].content, "parts", [])
                                texts = [p.text for p in parts if hasattr(p, "text") and p.text]
                                raw = "\n".join(texts)
                        except Exception:
                            raw = str(response)
                except Exception as e:
                    raw = f"Gemini error: {e}"

            last_raw = raw
            names = AIService._normalize_card_names(raw)
            if candidates:
                names = AIService._apply_candidate_matching(names, candidates)
            if names:
                return names, raw
            if not AIService._is_refusal_text(raw):
                break

        return [], last_raw

    @staticmethod
    def _generate_content_with_retries(models_obj, model_id, contents, max_attempts: int = 3, initial_delay: float = 1.0):
        """Call models.generate_content with simple retries and exponential backoff.

        - `models_obj`: the `client.models` object
        - `model_id`: model string
        - `contents`: contents argument passed through
        - `max_attempts`: total attempts (default 3)
        - `initial_delay`: seconds before first retry (default 1.0)
        """
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                return models_obj.generate_content(model=model_id, contents=contents)
            except Exception as e:
                last_exc = e
                if attempt >= max_attempts:
                    logger.warning("generate_content failed after %s attempts", attempt)
                    raise
                # Log and sleep before retrying
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning("generate_content attempt %s failed: %s; retrying in %.1fs", attempt, e, delay)
                time.sleep(delay)
        # If we exit loop unexpectedly, re-raise last exception
        if last_exc:
            raise last_exc

    @staticmethod
    def _rotate_image_bytes(image_bytes: bytes, rotation_degrees: int, mime_type: str) -> tuple[bytes, str]:
        if rotation_degrees % 360 == 0:
            return image_bytes, mime_type

        if not _pillow_available:
            return image_bytes, mime_type

        with BytesIO(image_bytes) as source_buffer:
            image = Image.open(source_buffer)
            rotated = image.rotate(-rotation_degrees, expand=True)

            output_mime = mime_type or "image/jpeg"
            output_format = "JPEG"
            if "png" in output_mime.lower():
                output_format = "PNG"
            elif "webp" in output_mime.lower():
                output_format = "WEBP"

            with BytesIO() as output_buffer:
                if output_format == "JPEG" and rotated.mode not in ("RGB", "L"):
                    rotated = rotated.convert("RGB")
                rotated.save(output_buffer, format=output_format)
                return output_buffer.getvalue(), output_mime

    @staticmethod
    def _normalize_image_orientation_by_exif(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
        if not _pillow_available:
            return image_bytes, mime_type

        try:
            with BytesIO(image_bytes) as source_buffer:
                image = Image.open(source_buffer)
                normalized = ImageOps.exif_transpose(image)

                output_mime = mime_type or "image/jpeg"
                output_format = "JPEG"
                if "png" in output_mime.lower():
                    output_format = "PNG"
                elif "webp" in output_mime.lower():
                    output_format = "WEBP"

                with BytesIO() as output_buffer:
                    if output_format == "JPEG" and normalized.mode not in ("RGB", "L"):
                        normalized = normalized.convert("RGB")
                    normalized.save(output_buffer, format=output_format)
                    return output_buffer.getvalue(), output_mime
        except Exception:
            return image_bytes, mime_type

    @staticmethod
    def _projection_variance_score(image: Image.Image) -> float:
        processed = ImageOps.autocontrast(image.convert("L"))
        processed.thumbnail((900, 900))
        bw = processed.point(lambda p: 255 if p > 165 else 0, mode="1")
        width, height = bw.size
        pixels = bw.load()

        if width == 0 or height == 0:
            return 0.0

        row_dark_counts: list[int] = []
        for y in range(height):
            dark_count = 0
            for x in range(width):
                if pixels[x, y] == 0:
                    dark_count += 1
            row_dark_counts.append(dark_count)

        mean = sum(row_dark_counts) / len(row_dark_counts)
        variance = sum((value - mean) ** 2 for value in row_dark_counts) / len(row_dark_counts)
        return variance

    @staticmethod
    def _estimate_rotation_candidates(image_bytes: bytes) -> list[int]:
        if not _pillow_available:
            return [0], {"0": 0.0, "90": 0.0}

        try:
            with BytesIO(image_bytes) as source_buffer:
                image = Image.open(source_buffer)
                upright_score = AIService._projection_variance_score(image)
                right_score = AIService._projection_variance_score(image.rotate(-90, expand=True))

                if right_score > (upright_score * 1.05):
                    return [90, 270], {"0": upright_score, "90": right_score}
                return [0, 180], {"0": upright_score, "90": right_score}
        except Exception:
            return [0, 180], {"0": 0.0, "90": 0.0}

    @staticmethod
    def _image_quality_signals(image_bytes: bytes) -> dict[str, float]:
        if not _pillow_available:
            return {}

        try:
            with BytesIO(image_bytes) as source_buffer:
                image = Image.open(source_buffer)
                gray = image.convert("L")
                stat = ImageStat.Stat(gray)
                brightness_mean = float(stat.mean[0])
                brightness_std = float(stat.stddev[0])

                edges = gray.filter(ImageFilter.FIND_EDGES)
                edge_stat = ImageStat.Stat(edges)
                edge_mean = float(edge_stat.mean[0])

                bw = ImageOps.autocontrast(gray).point(lambda p: 255 if p > 165 else 0, mode="1")
                width, height = bw.size
                pixels = bw.load()
                total = max(1, width * height)
                dark = 0
                for y in range(height):
                    for x in range(width):
                        if pixels[x, y] == 0:
                            dark += 1
                dark_ratio = dark / total

                aspect_ratio = (float(image.width) / float(image.height)) if image.height else 0.0
                return {
                    "width": float(image.width),
                    "height": float(image.height),
                    "aspect_ratio": aspect_ratio,
                    "brightness_mean": brightness_mean,
                    "brightness_std": brightness_std,
                    "edge_mean": edge_mean,
                    "dark_ratio": dark_ratio,
                }
        except Exception:
            return {}

    @staticmethod
    def _likely_recognition_issues(signals: dict[str, float]) -> list[str]:
        if not signals:
            return []

        issues: list[str] = []
        width = signals.get("width", 0.0)
        height = signals.get("height", 0.0)
        brightness = signals.get("brightness_mean", 0.0)
        contrast = signals.get("brightness_std", 0.0)
        edge = signals.get("edge_mean", 0.0)
        dark_ratio = signals.get("dark_ratio", 0.0)

        if width < 1400 or height < 1000:
            issues.append("Low resolution: card title text may be too small")
        if brightness < 70:
            issues.append("Image appears dark/underexposed")
        if brightness > 205:
            issues.append("Image appears overexposed or washed out")
        if contrast < 28:
            issues.append("Low contrast: titles may blend into background")
        if edge < 12:
            issues.append("Low edge detail: possible blur/focus issue")
        if dark_ratio < 0.06:
            issues.append("Very little text-like dark content detected")

        return issues

    # ------------------------------------------------------------------
    # Deck description
    # ------------------------------------------------------------------
    @staticmethod
    def generate_deck_description(
        player_name: Optional[str],
        deck_name: Optional[str],
        card_names: list[str],
        record: Optional[str] = None,
    ) -> str:
        """
        Generate a short prose description of a draft deck.
        card_names: list of card names in the main deck.
        """
        client = _get_client()
        card_list = "\n".join(card_names) if card_names else "(no cards listed)"
        prompt = (
            f"You are a Magic: The Gathering draft analyst. "
            f"Describe this draft deck in 2-4 sentences covering its strategy, key cards, and overall power level.\n\n"
            f"Player: {player_name or 'Unknown'}\n"
            f"Deck name: {deck_name or 'Unnamed'}\n"
            f"Record: {record or 'N/A'}\n"
            f"Main deck cards:\n{card_list}"
        )

        text_model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        try:
            models = getattr(client, "models", None)
            if models is None and hasattr(client, "Client"):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                models = client.models

            response = models.generate_content(model=text_model, contents=prompt)
            text = getattr(response, "text", None)
            if not text:
                cand = getattr(response, "candidates", None) or getattr(response, "output", None)
                if cand and len(cand) > 0:
                    parts = getattr(cand[0].content, "parts", [])
                    texts = [p.text for p in parts if hasattr(p, "text") and p.text]
                    text = "\n".join(texts)
            return (text or "").strip()
        except Exception:
            raise

    # ------------------------------------------------------------------
    # Deck archetype tags
    # ------------------------------------------------------------------
    @staticmethod
    def generate_deck_tags(card_names: list[str]) -> dict:
        """
        Return {"archetype": str, "archetype_detail": str} for a deck.

        archetype is one of: aggro, midrange, control, combo, other
        archetype_detail is a short freeform label, e.g. "red aggro", "aristocrats",
        "reanimator", "spellslinger", "white weenie", "ramp".
        Returns empty strings on failure so callers can gracefully skip.
        """
        client = _get_client()
        card_list = "\n".join(card_names) if card_names else "(no cards)"
        prompt = (
            "You are a Magic: The Gathering draft analyst.\n"
            "Given the following main deck card list, classify the deck.\n\n"
            f"Cards:\n{card_list}\n\n"
            "Respond with ONLY a JSON object (no markdown, no explanation) in this exact format:\n"
            '{"archetype": "<aggro|midrange|control|combo|other>", '
            '"archetype_detail": "<short specific label>"}\n'
            "The archetype_detail should be 1-3 words like 'red aggro', 'aristocrats', "
            "'reanimator', 'spellslinger', 'white weenie', 'ramp', 'tempo', etc."
        )
        text_model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        try:
            models = getattr(client, "models", None)
            if models is None and hasattr(client, "Client"):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                models = client.models

            response = AIService._generate_content_with_retries(models, text_model, prompt)
            raw = getattr(response, "text", None) or ""
            if not raw:
                cand = getattr(response, "candidates", None)
                if cand and len(cand) > 0:
                    parts = getattr(cand[0].content, "parts", [])
                    raw = "\n".join(p.text for p in parts if hasattr(p, "text") and p.text)
            raw = raw.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
            parsed = json.loads(raw)
            return {
                "archetype": str(parsed.get("archetype", "")).lower().strip(),
                "archetype_detail": str(parsed.get("archetype_detail", "")).lower().strip(),
            }
        except Exception:
            logger.warning("generate_deck_tags failed", exc_info=True)
            return {"archetype": "", "archetype_detail": ""}

    # ------------------------------------------------------------------
    # Draft narrative summary
    # ------------------------------------------------------------------
    @staticmethod
    def generate_draft_summary(
        draft_name: Optional[str],
        cube_name: Optional[str],
        decks: list[dict],
        rounds: Optional[list[dict]] = None,
        feedback: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate a detailed, multi-section narrative summary of an entire draft.

        Each deck dict should contain:
          player_name, deck_name, record, ai_description, card_names (list[str])

        Each round dict (optional):
          round_num, pairings: [{p1_name, p2_name, p1_wins, p2_wins, winner_name}]

        Each feedback dict (optional):
          player_name, rating, thoughts, recommendations
        """
        client = _get_client()

        # ── Build per-deck section ──────────────────────────────────────
        deck_sections = []
        for d in decks:
            name = d.get("player_name") or "Unknown"
            deck_name = d.get("deck_name") or "Unnamed"
            rec = d.get("record") or "N/A"
            desc = d.get("ai_description") or ""
            cards = d.get("card_names") or []
            card_list_str = ", ".join(cards) if cards else "(no card list)"

            section = f"### {name} — \"{deck_name}\" [{rec}]\n"
            if desc:
                section += f"Deck description: {desc}\n"
            section += f"Cards ({len(cards)}): {card_list_str}"
            deck_sections.append(section)

        decks_text = "\n\n".join(deck_sections) if deck_sections else "(no deck data)"

        # ── Build rounds/matchups section ───────────────────────────────
        rounds_text = ""
        if rounds:
            round_lines = []
            for r in rounds:
                rn = r.get("round_num", "?")
                pairings_str = []
                for p in r.get("pairings", []):
                    p1 = p.get("p1_name", "?")
                    p2 = p.get("p2_name", "BYE")
                    p1w = p.get("p1_wins", 0)
                    p2w = p.get("p2_wins", 0)
                    winner = p.get("winner_name", "")
                    if p2 == "BYE":
                        pairings_str.append(f"  {p1} received a BYE")
                    else:
                        result = f"{p1} {p1w}-{p2w} {p2}"
                        if winner:
                            result += f" → {winner} wins"
                        pairings_str.append(f"  {result}")
                round_lines.append(f"Round {rn}:\n" + "\n".join(pairings_str))
            rounds_text = "\n\n".join(round_lines)

        # ── Build feedback section ──────────────────────────────────────
        feedback_text = ""
        if feedback:
            fb_lines = []
            for fb in feedback:
                pn = fb.get("player_name") or "Anonymous"
                rating = fb.get("rating")
                thoughts = fb.get("thoughts") or ""
                recs = fb.get("recommendations") or ""
                line = f"  {pn}"
                if rating:
                    line += f" (rated {rating}/10)"
                if thoughts:
                    line += f": \"{thoughts}\""
                if recs:
                    line += f" | Recs: \"{recs}\""
                fb_lines.append(line)
            feedback_text = "\n".join(fb_lines)

        # ── Build the master prompt ─────────────────────────────────────
        prompt_parts = [
            "You are a friendly Magic: The Gathering draft analyst writing a summary for a group of friends who drafted together.",
            "Write a clear, honest, conversational summary of the following draft. Keep the tone casual and direct — like you're recapping it for the players themselves, not writing tournament coverage.",
            "Your summary should include the following sections:\n",
            "**1. Draft Overview** — A quick intro: what cube was drafted, who played, and who came out on top. Mention any notable patterns in what colors or strategies got drafted. 1-2 paragraphs.\n",
            "**2. Deck Breakdowns** — For EACH player write a short section covering:",
            "   - What the deck was trying to do",
            "   - A few standout cards",
            "   - How it performed",
            "   Keep each player section to 2-3 paragraphs.\n",
            "**3. Matchup Recap** — If round data is available, briefly describe what happened in the notable matches. If not, touch on how the decks would have matched up.\n",
            "**4. Player Feedback & Cube Notes** (if feedback is available) — Summarise what players thought. What cards impressed people? What felt weak? Any suggestions worth flagging for the cube owner.\n",
            "**5. Final Thoughts** — One short closing paragraph on how the draft went overall.\n",
            "Use the players' real names. Reference actual card names. Be specific but keep it readable — no need to be exhaustive.\n",
            "---",
            f"Draft: {draft_name or 'Unnamed Draft'}",
            f"Cube: {cube_name or 'Unknown Cube'}\n",
            "=== DECKS ===\n" + decks_text,
        ]
        if rounds_text:
            prompt_parts.append("\n=== ROUND RESULTS ===\n" + rounds_text)
        if feedback_text:
            prompt_parts.append("\n=== PLAYER FEEDBACK ===\n" + feedback_text)

        prompt = "\n".join(prompt_parts)

        text_model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        try:
            models = getattr(client, "models", None)
            if models is None and hasattr(client, "Client"):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                models = client.models

            response = models.generate_content(model=text_model, contents=prompt)
            text = getattr(response, "text", None)
            if not text:
                cand = getattr(response, "candidates", None) or getattr(response, "output", None)
                if cand and len(cand) > 0:
                    parts = getattr(cand[0].content, "parts", [])
                    texts = [p.text for p in parts if hasattr(p, "text") and p.text]
                    text = "\n".join(texts)
            return (text or "").strip()
        except Exception:
            raise

    # ------------------------------------------------------------------
    # Card recognition from deck photo (vision)
    # ------------------------------------------------------------------
    @staticmethod
    def identify_cards_from_photo(
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        candidate_card_names: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Given a photo of a deck laid out, return a list of card names.
        Returns a list of strings (card names as identified by the model).
        """
        client = _get_client()
        candidates = [c.strip() for c in (candidate_card_names or []) if c and c.strip()]

        # Build the prompt exactly as you requested
        if candidates:
            prompt = "Tell me what cards are in this photo. Ignore basic lands. They will only be from this list:\n" + "\n".join(candidates)
        else:
            prompt = "Tell me what cards are in this photo. Ignore basic lands. List identified cards one per line."

        try:
            models = getattr(client, "models", None)
            if models is None and hasattr(client, "Client"):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                models = client.models

            model_id = os.getenv("GEMINI_VISION_MODEL", "gemini-3-flash-preview")

            pil_image = None
            if _pillow_available:
                with BytesIO(image_bytes) as b:
                    pil_image = Image.open(b).convert("RGB")

            # Preferred simple single-shot call: send [prompt, PIL Image]
            if pil_image is not None:
                response = AIService._generate_content_with_retries(models, model_id, [prompt, pil_image])
            else:
                # Fallback to inlineData if PIL isn't available
                contents = {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": mime_type, "data": image_bytes}},
                    ],
                }
                response = AIService._generate_content_with_retries(models, model_id, contents)

            raw = getattr(response, "text", None) or ""
            if not raw:
                cand = getattr(response, "candidates", None) or getattr(response, "output", None)
                if cand and len(cand) > 0:
                    parts = getattr(cand[0].content, "parts", [])
                    texts = [p.text for p in parts if hasattr(p, "text") and p.text]
                    raw = "\n".join(texts)

            names = AIService._normalize_card_names(raw)
            if candidates:
                names = AIService._apply_candidate_matching(names, candidates)

            return names
        except Exception:
            logger.exception("identify_cards_from_photo failed")
            raise
