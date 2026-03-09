import requests
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ScryfallService:
    """Service for fetching card data from the Scryfall API."""
    
    BASE_URL = "https://api.scryfall.com"
    
    @staticmethod
    def get_card_by_name(card_name: str) -> Optional[Dict[str, Any]]:
        """
        Get card data from Scryfall by exact card name.
        
        Args:
            card_name: The name of the card to search for
            
        Returns:
            Dictionary with card data or None if not found
        """
        try:
            url = f"{ScryfallService.BASE_URL}/cards/named"
            params = {"exact": card_name}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Card not found on Scryfall: {card_name}")
                return None
            logger.error(f"Scryfall API error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Scryfall API: {e}")
            return None
    
    @staticmethod
    def get_card_by_id(scryfall_id: str) -> Optional[Dict[str, Any]]:
        """
        Get card data from Scryfall by Scryfall ID.
        
        Args:
            scryfall_id: The Scryfall UUID of the card
            
        Returns:
            Dictionary with card data or None if not found
        """
        try:
            url = f"{ScryfallService.BASE_URL}/cards/{scryfall_id}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Card not found on Scryfall: {scryfall_id}")
                return None
            logger.error(f"Scryfall API error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Scryfall API: {e}")
            return None
    
    @staticmethod
    def search_cards(query: str, limit: int = 20) -> Optional[list[Dict[str, Any]]]:
        """
        Search for cards on Scryfall.
        
        Args:
            query: The search query (can use Scryfall search syntax)
            limit: Maximum number of results to return
            
        Returns:
            List of card data dictionaries or None on error
        """
        try:
            url = f"{ScryfallService.BASE_URL}/cards/search"
            params = {
                "q": query,
                "unique": "prints",  # One printing per card
                "order": "name"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            cards = data.get("data", [])
            
            return cards[:limit]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Scryfall: {e}")
            return None
    
    @staticmethod
    def _fetch_card_exact(card_name: str) -> Optional[Dict[str, Any]]:
        """
        Try to fetch a single card from Scryfall by exact name.
        Uses /cards/named?exact=... which also resolves promo/flavor names
        (e.g. Godzilla series) and double-faced card full names.
        """
        try:
            response = requests.get(
                f"{ScryfallService.BASE_URL}/cards/named",
                params={"exact": card_name},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return None

    @staticmethod
    def get_cards_by_names_bulk(card_names: list[str]) -> Dict[str, Any]:
        """
        Fetch multiple cards from Scryfall using the /cards/collection endpoint.
        Supports up to 75 cards per request; automatically batches larger lists.

        For names that the collection endpoint cannot match, a per-card fallback
        is used:
          1. GET /cards/named?exact=<name>  – resolves flavor/promo names such as
             Godzilla variants.
          2. If the name contains ' // ' (double-faced card), retry with just the
             front-face name.

        Args:
            card_names: List of card names to fetch

        Returns:
            Dictionary with:
                "found": list of Scryfall card dicts that were matched
                "not_found": list of name strings that could not be resolved
        """
        found = []
        still_not_found: list[str] = []
        BATCH_SIZE = 75

        for i in range(0, len(card_names), BATCH_SIZE):
            batch = card_names[i : i + BATCH_SIZE]
            identifiers = [{"name": name} for name in batch]
            try:
                url = f"{ScryfallService.BASE_URL}/cards/collection"
                payload = {"identifiers": identifiers}
                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                found.extend(data.get("data", []))
                # Scryfall returns not_found as list of identifier dicts
                for item in data.get("not_found", []):
                    still_not_found.append(item.get("name", ""))
            except requests.exceptions.RequestException as e:
                logger.error(f"Error bulk-fetching cards from Scryfall: {e}")
                still_not_found.extend(batch)

        # --- Fallback pass for unresolved names ---
        final_not_found: list[str] = []
        for name in still_not_found:
            if not name:
                continue
            # Attempt 1: exact name lookup (handles flavor/promo names)
            card = ScryfallService._fetch_card_exact(name)
            if card:
                found.append(card)
                continue
            # Attempt 2: for DFC notation "Front // Back", try front face only
            if " // " in name:
                front_face = name.split(" // ")[0].strip()
                card = ScryfallService._fetch_card_exact(front_face)
                if card:
                    found.append(card)
                    continue
            final_not_found.append(name)

        return {"found": found, "not_found": final_not_found}

    @staticmethod
    def extract_card_info(scryfall_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant card information from Scryfall response.
        
        Args:
            scryfall_data: Full card data from Scryfall API
            
        Returns:
            Dictionary with key card information
        """
        return {
            "id": scryfall_data.get("id"),
            "name": scryfall_data.get("name"),
            "mana_cost": scryfall_data.get("mana_cost"),
            "type_line": scryfall_data.get("type_line"),
            "colors": scryfall_data.get("colors", []),
            "cmc": scryfall_data.get("cmc"),
            "power": scryfall_data.get("power"),
            "toughness": scryfall_data.get("toughness"),
            "text": scryfall_data.get("oracle_text"),
            "image_url": scryfall_data.get("image_uris", {}).get("normal"),
            "small_image_url": scryfall_data.get("image_uris", {}).get("small"),
            "rarity": scryfall_data.get("rarity"),
            "set": scryfall_data.get("set"),
            "set_name": scryfall_data.get("set_name"),
            "scryfall_uri": scryfall_data.get("scryfall_uri")
        }
    
    @staticmethod
    def get_card_info_cached(db, card_service, card_id: int, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get card info from cache or fetch from Scryfall.
        
        Args:
            db: Database session
            card_service: CardService instance
            card_id: Database card ID
            refresh: Force refresh from Scryfall even if cached
            
        Returns:
            Dictionary with card information or None
        """
        card = card_service.get_card_by_id(db, card_id)
        if not card:
            return None
        
        # Check if cached data exists and refresh not requested
        if card.cached_data and not refresh:
            try:
                return json.loads(card.cached_data)
            except json.JSONDecodeError:
                pass
        
        # Fetch from Scryfall
        scryfall_data = ScryfallService.get_card_by_id(card.scryfall_id)
        
        if scryfall_data:
            card_info = ScryfallService.extract_card_info(scryfall_data)
            
            # Cache the data
            card_service.update_cached_data(db, card_id, json.dumps(card_info))
            
            return card_info
        
        return None
