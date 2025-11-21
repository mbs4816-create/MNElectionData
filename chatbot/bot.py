"""Chatbot that can answer simple questions about Minnesota election data."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, List

from . import data_access
from .parsers import ParsedRequest, parse_request


OFFICE_KEYWORDS: Dict[str, List[str]] = {
    "president": ["president"],
    "governor": ["governor"],
    "senate": ["senate"],
    "house": ["house"],
    "attorney general": ["attorney", "general"],
    "secretary of state": ["secretary", "state"],
    "auditor": ["auditor"],
}


KML_FILES = [
    "2024_Results/mn-cd1-precincts.kml",
    "2024_Results/mn-cd2-precincts.kml",
    "2024_Results/mn-cd3-precincts.kml",
    "2024_Results/mn-cd4-precincts.kml",
    "2024_Results/mn-cd5-precincts.kml",
    "2024_Results/mn-cd6-precincts.kml",
    "2024_Results/mn-cd7-precincts.kml",
    "2024_Results/mn-cd8-precincts.kml",
]


class ElectionChatbot:
    """Very small helper to field structured questions about the tabular files."""

    def __init__(self) -> None:
        self._years = data_access.available_years()

    def reply(self, message: str) -> str:
        request = parse_request(message)
        if request.wants_map:
            return self._map_response()

        if not request.year:
            return self._prompt_for_year()

        if request.year not in self._years:
            return (
                f"I can only answer questions for {', '.join(str(y) for y in self._years)}."
            )

        if not request.office_key:
            return "Please specify an office, such as president, governor, or attorney general."

        return self._summarize_results(request)

    def _prompt_for_year(self) -> str:
        return (
            "I need to know which election year you care about. "
            f"Try asking about {'/'.join(str(y) for y in self._years)}."
        )

    def _map_response(self) -> str:
        file_list = ", ".join(KML_FILES)
        return (
            "Load the 2024 congressional-district KMLs into QGIS, Mapbox, or Kepler.gl. "
            f"You'll find them in: {file_list}. Combine them with the aggregated vote "
            "totals from the CSV query results to create the requested map."
        )

    def _summarize_results(self, request: ParsedRequest) -> str:
        office_keywords = OFFICE_KEYWORDS.get(request.office_key, [request.office_key])
        try:
            rows = data_access.summarize_office(
                year=request.year,
                office_keywords=office_keywords,
                county_name=request.county,
            )
        except data_access.ElectionDataAccessError as exc:
            return str(exc)

        if not rows:
            scope = "statewide" if not request.county else f"{request.county} County"
            return f"I could not find {request.office_key} results for {scope} in {request.year}."

        header = (
            f"{request.year} {rows[0]['office']} results"
            + (f" in {request.county} County" if request.county else " statewide")
        )

        lines = [header]
        for row in rows[:5]:
            district = f" ({row['district']})" if row["district"] else ""
            party = f"[{row['party']} ]" if row["party"] else ""
            lines.append(f"- {row['candidate']}{district} {party}- {row['votes']:,} votes")

        if len(rows) > 5:
            lines.append("Showing top 5 candidates. Refine your prompt for more detail.")

        return "\n".join(lines)
