"""Google Places API (New) client for local business discovery.

Requires a Google Places API key with the "Places API (New)" service enabled:
https://console.cloud.google.com/apis/library/places.googleapis.com
"""

import time

import requests

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.websiteUri",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.businessStatus",
        "places.rating",
        "places.userRatingCount",
        "places.googleMapsUri",
        "nextPageToken",
    ]
)


class PlacesError(RuntimeError):
    pass


class PlacesClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, niche: str, city: str, max_results: int = 60) -> list[dict]:
        """Return up to max_results businesses for `niche` in `city`."""
        results: list[dict] = []
        page_token = None
        while len(results) < max_results:
            body = {"textQuery": f"{niche} in {city}", "pageSize": 20}
            if page_token:
                body["pageToken"] = page_token
            resp = requests.post(
                TEXT_SEARCH_URL,
                json=body,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": FIELD_MASK,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
            if resp.status_code == 429:
                time.sleep(2)
                continue
            if resp.status_code != 200:
                raise PlacesError(
                    f"Places API error {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            for place in data.get("places", []):
                if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue
                results.append(
                    {
                        "place_id": place.get("id", ""),
                        "business_name": _display_name(place),
                        "address": place.get("formattedAddress", ""),
                        "phone": place.get("nationalPhoneNumber", ""),
                        "website": place.get("websiteUri", ""),
                        "rating": place.get("rating", ""),
                        "reviews": place.get("userRatingCount", ""),
                        "maps_url": place.get("googleMapsUri", ""),
                    }
                )
                if len(results) >= max_results:
                    break
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return results


def _display_name(place: dict) -> str:
    name = place.get("displayName")
    if isinstance(name, dict):
        return name.get("text", "")
    return name or ""
