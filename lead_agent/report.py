"""CSV report writer."""

import csv

FIELDS = [
    "score",
    "business_name",
    "phone",
    "address",
    "website",
    "rating",
    "reviews",
    "outdated_signals",
    "notes",
    "maps_url",
    "place_id",
]


def write_csv(path: str, leads: list[dict]) -> None:
    leads = sorted(leads, key=lambda lead: lead.get("score", 0), reverse=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = dict(lead)
            row["outdated_signals"] = ";".join(lead.get("signals", []))
            row["notes"] = "; ".join(lead.get("notes", []))
            writer.writerow(row)
