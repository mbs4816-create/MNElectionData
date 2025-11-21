"""Helpers that load Minnesota election result files on demand."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


RESULT_FILES = {
    2020: REPO_ROOT / "2020_Results" / "Federal_State_Local_2020.txt",
    2022: REPO_ROOT / "2022_Results" / "Federal_State_County_Precinct_2022",
    2024: REPO_ROOT / "2024_Results" / "Federal_State_County_ByPrecinct_2024",
}

COUNTY_FILES = {
    2020: REPO_ROOT / "2020_Results" / "Counties_2020.txt",
    2022: REPO_ROOT / "2022_Results" / "Counties_2022",
    2024: REPO_ROOT / "2024_Results" / "Counties_2024",
}

FIELDNAMES = [
    "State",
    "CountyID",
    "PrecinctName",
    "OfficeID",
    "OfficeName",
    "District",
    "CandidateOrderCode",
    "CandidateName",
    "Suffix",
    "IncumbentCode",
    "PartyAbbreviation",
    "PrecinctsReporting",
    "TotalPrecincts",
    "Votes",
    "Percent",
    "OfficeVotes",
]

_COUNTY_CACHE: Dict[int, Dict[str, str]] = {}


class ElectionDataAccessError(RuntimeError):
    """Raised when a query is malformed or the requested file is missing."""


def _ensure_file(path: Path) -> Path:
    if not path.exists():
        raise ElectionDataAccessError(f"Result file not found: {path}")
    return path


def available_years() -> List[int]:
    return [year for year, path in RESULT_FILES.items() if path.exists()]


def _county_lookup(year: int) -> Dict[str, str]:
    if year in _COUNTY_CACHE:
        return _COUNTY_CACHE[year]

    lookup: Dict[str, str] = {}
    county_path = COUNTY_FILES.get(year)
    if county_path and county_path.exists():
        with county_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                parts = [part.strip() for part in line.strip().split(";") if part.strip()]
                if len(parts) >= 2:
                    lookup[parts[1].lower()] = parts[0]

    _COUNTY_CACHE[year] = lookup
    return lookup


def summarize_office(
    *,
    year: int,
    office_keywords: Iterable[str],
    county_name: Optional[str] = None,
) -> List[dict]:
    """Return vote totals for an office filtered by county (if provided)."""

    path = _ensure_file(RESULT_FILES[year])
    keywords = [kw.lower() for kw in office_keywords if kw]
    if not keywords:
        raise ElectionDataAccessError("At least one office keyword is required")

    county_id: Optional[str] = None
    if county_name:
        lookup = _county_lookup(year)
        county_id = lookup.get(county_name.lower())
        if county_id is None:
            raise ElectionDataAccessError(
                f"County '{county_name}' was not found in the {year} lookup table."
            )

    totals: Dict[tuple, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", fieldnames=FIELDNAMES)
        for row in reader:
            office = row.get("OfficeName", "")
            if not office:
                continue

            state_value = row.get("State", "").strip().lower()
            if state_value == "state":
                # Some files repeat their header row at the top.
                continue

            lower_office = office.lower()
            if not all(keyword in lower_office for keyword in keywords):
                continue

            if county_id and row.get("CountyID", "").strip() != county_id:
                    continue

            key = (
                row.get("OfficeName", ""),
                row.get("District", ""),
                row.get("CandidateName", ""),
                row.get("PartyAbbreviation", ""),
            )

            try:
                vote_value = int(float(row.get("Votes", "0") or 0))
            except ValueError:
                vote_value = 0

            totals[key] = totals.get(key, 0) + vote_value

    results = [
        {
            "office": key[0],
            "district": key[1],
            "candidate": key[2],
            "party": key[3],
            "votes": votes,
        }
        for key, votes in totals.items()
    ]

    results.sort(key=lambda item: item["votes"], reverse=True)
    return results
