"""Very small NLP helpers for the election chatbot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


YEAR_PATTERN = re.compile(r"(20[2-4][0-9])")


OFFICE_SYNONYMS = {
    "president": ["president", "presidential"],
    "governor": ["governor", "gubernatorial"],
    "senate": ["senate", "senator"],
    "house": ["house", "representative"],
    "attorney general": ["attorney", "attorney general"],
    "secretary of state": ["secretary of state"],
    "auditor": ["auditor"],
}


MAP_KEYWORDS = {"map", "shape", "shapefile", "boundary", "kml"}


@dataclass
class ParsedRequest:
    year: Optional[int]
    office_key: Optional[str]
    county: Optional[str]
    wants_map: bool


def parse_year(message: str) -> Optional[int]:
    match = YEAR_PATTERN.search(message)
    if match:
        return int(match.group(1))
    return None


def parse_office(message: str) -> Optional[str]:
    lower = message.lower()
    for key, keywords in OFFICE_SYNONYMS.items():
        if any(keyword in lower for keyword in keywords):
            return key
    return None


def parse_county(message: str) -> Optional[str]:
    match = re.search(r"([A-Z][a-z]+\sCounty)", message)
    if match:
        return match.group(1).replace(" County", "")
    return None


def parse_request(message: str) -> ParsedRequest:
    lower = message.lower()
    wants_map = any(keyword in lower for keyword in MAP_KEYWORDS)
    return ParsedRequest(
        year=parse_year(message),
        office_key=parse_office(message),
        county=parse_county(message),
        wants_map=wants_map,
    )
