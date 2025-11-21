"""Infer which offices (statewide plus municipal/school) return to the 2026 ballot."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

import chatbot.data_access as data_access


YEARS_TO_ANALYZE: Sequence[int] = (2020, 2022, 2024)
OUTPUT_FILE = Path("predicted_2026_ballot.csv")

# Municipal, hospital, and school district contests are stored in companion files
# that mirror the statewide schema.  Pull them into the cadence calculation so we
# do not miss local offices that only live in those exports.
LOCAL_RESULT_FILES = {
    2020: data_access.REPO_ROOT / "2020_Results" / "Muni_Hospital_School_2020.txt",
    2022: data_access.REPO_ROOT / "2022_Results" / "Municipal_Hospital_School_Precinct_2022",
    2024: data_access.REPO_ROOT / "2024_Results" / "All_MuniHospitalSchoolDistritct_2024",
}


def _result_files_for_year(year: int) -> List[Path]:
    files: List[Path] = []
    statewide = data_access.RESULT_FILES.get(year)
    if statewide and statewide.exists():
        files.append(statewide)

    local = LOCAL_RESULT_FILES.get(year)
    if local and local.exists():
        files.append(local)

    return files


def _iter_offices() -> Dict[str, Set[int]]:
    offices: Dict[str, Set[int]] = {}
    for year in YEARS_TO_ANALYZE:
        for path in _result_files_for_year(year):
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(
                    handle,
                    delimiter=";",
                    fieldnames=data_access.FIELDNAMES,
                )
                for row in reader:
                    office = (row.get("OfficeName") or "").strip()
                    if not office or office.lower() == "officename":
                        continue
                    offices.setdefault(office, set()).add(year)
    return offices


def _infer_cycle(years: Sequence[int]) -> Optional[int]:
    if len(years) < 2:
        return None
    diffs = [b - a for a, b in zip(years, years[1:])]
    if all(diff == 2 for diff in diffs):
        return 2
    if all(diff == 4 for diff in diffs):
        return 4
    return None


def _prediction_reason(years: Sequence[int], cycle: Optional[int]) -> str:
    if cycle is not None:
        return f"Observed {cycle}-year cadence across {', '.join(map(str, years))}."
    if years[-1] == 2022:
        return "Only observed in the 2022 midterm, so assume the 4-year midterm cycle."
    if years[-1] == 2024 and len(years) > 1 and years[-2] == 2022:
        return (
            "Appeared in consecutive general elections (2022, 2024); "
            "assume the 2-year election cycle continues."
        )
    return "No reliable cadence detected from available years."


def predict_2026_offices() -> List[dict]:
    offices = _iter_offices()
    predictions: List[dict] = []
    for office, years in offices.items():
        sorted_years = sorted(years)
        last_year = sorted_years[-1]
        if last_year < 2022:
            continue

        cycle = _infer_cycle(sorted_years)
        if cycle is not None:
            next_year = last_year + cycle
        elif last_year == 2022:
            next_year = 2026
        elif last_year == 2024 and len(sorted_years) > 1 and sorted_years[-2] == 2022:
            next_year = 2026
        else:
            next_year = None

        if next_year != 2026:
            continue

        predictions.append(
            {
                "OfficeName": office,
                "ObservedYears": "|".join(str(year) for year in sorted_years),
                "CycleEstimate": f"{cycle}-year" if cycle else "heuristic",
                "PredictionReason": _prediction_reason(sorted_years, cycle),
            }
        )

    predictions.sort(key=lambda item: item["OfficeName"].lower())
    return predictions


def write_predictions(path: Path = OUTPUT_FILE) -> int:
    predictions = predict_2026_offices()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["OfficeName", "ObservedYears", "CycleEstimate", "PredictionReason"],
        )
        writer.writeheader()
        writer.writerows(predictions)
    return len(predictions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help="Where to write the CSV summary (default: predicted_2026_ballot.csv)",
    )
    args = parser.parse_args()
    count = write_predictions(args.output)
    print(f"Wrote {count} predicted offices to {args.output}")


if __name__ == "__main__":
    main()
