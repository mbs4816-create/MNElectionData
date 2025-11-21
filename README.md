# Minnesota Election Data Repository

## Overview
This repository mirrors the flat files that the Minnesota Secretary of State (OSS) publishes for the 2020, 2022, and 2024 State General Elections.  Every text file is ASCII encoded, semicolon-delimited, and structured so that each row represents the result for a single candidate or ballot question response within a specific geography (statewide, county, district, or precinct, depending on the file).【F:2020_Results/Text_File_Layout_2020.txt†L1-L40】【F:2024_Results/2024_TextFile_Layout†L1-L40】  OSS also notes that precinct-level files are posted the morning after election day, write-in candidates share the order code `9901`, and all local races are treated as non-partisan contests.【F:2024_Results/2024_TextFile_Layout†L6-L44】

Alongside the result files you will find supporting lookup tables (parties, counties, precinct definitions, municipalities, school districts, and candidate contact data) that allow you to normalize the identifiers used across years.【F:2020_Results/Text_File_Layout_2020.txt†L82-L226】【F:2024_Results/2024_TextFile_Layout†L63-L209】  All text files replace embedded semicolons inside address or question text with caret (`^`) characters, which is important if you need to reconstruct the original strings.【F:2020_Results/Text_File_Layout_2020.txt†L154-L208】

## Repository layout
```
MNElectionData/
├── 2020_Results/
├── 2022_Results/
└── 2024_Results/
```
Each directory corresponds to one general election and contains the tabular exports plus its authoritative "Text File Layout" that documents every column.

## Working with the results

### Common columns
Use the following shared fields when you ingest a results file:

| Field | Description |
| --- | --- |
| `State`, `County ID`, `Precinct name` | Identify the geography at which votes were reported. County and precinct IDs link to the supporting tables below.【F:2020_Results/Text_File_Layout_2020.txt†L24-L39】【F:2024_Results/2024_TextFile_Layout†L24-L39】 |
| `Office ID`, `Office Name`, `District` | Identify the race being reported. The district field covers congressional, legislative, county commissioner, judicial, municipal FIPS, school district, and other local districts, but is blank for statewide offices.【F:2020_Results/Text_File_Layout_2020.txt†L24-L42】 |
| `Candidate Order Code`, `Candidate Name`, `Party Abbreviation` | Distinguish each candidate or response. Write-ins always use order code `9901` and local races omit party labels beyond `NP` (non-partisan).【F:2024_Results/2024_TextFile_Layout†L30-L44】 |
| `Precincts reporting`, `Total precincts`, `Votes`, `Percent`, `Total votes for office` | Raw vote totals as well as the share of the office vote earned by the row's candidate.【F:2020_Results/Text_File_Layout_2020.txt†L34-L39】 |

Precinct voting statistics (`pctstats.txt` in each folder) add election-day registration and ballot-type counts for every precinct, which is useful for turnout analyses.【F:2024_Results/2024_TextFile_Layout†L47-L60】

### Supporting lookup tables
These helpers are consistent across years:

* **Parties** – Abbreviation, full party name, and numeric ID. Example rows in 2024 include Republican (`R`), DFL, Libertarian, and write-in codes.【F:2024_Results/Parties_2024†L1-L15】
* **Counties** – County ID, name, and the number of precincts reported for that county.【F:2024_Results/Counties_2024†L1-L10】
* **Precincts** – County and precinct IDs, precinct names, and crosswalks to congressional, legislative, commissioner, judicial, soil & water, MCD FIPS, and school districts.【F:2024_Results/2024_TextFile_Layout†L84-L98】【F:2024_Results/Precincts_2024†L1-L5】
* **Municipalities (mcdtbl)** – County information plus the municipality's FIPS code and name, enabling joins to local contests.【F:2024_Results/2024_TextFile_Layout†L204-L209】【F:2020_Results/Municipalities_2020.txt†L1-L5】
* **School districts** – School district numbers, names, and their home county.【F:2020_Results/Text_File_Layout_2020.txt†L212-L218】
* **Candidate rosters** – `cand.txt` and `CandTbl.txt` cover federal/state/county contests, while `LocalCandTbl.txt` and `LocalCandDetails.txt` store identifiers and optional contact information for municipal, school district, hospital, and special district races.【F:2020_Results/Text_File_Layout_2020.txt†L118-L194】
* **Ballot questions** – Each row documents the jurisdiction identifiers plus the question title and body with carets instead of semicolons.【F:2020_Results/Text_File_Layout_2020.txt†L198-L209】

### Precinct-level results vs. local contests
The state splits its exports so that federal/state/county races appear in one file per year and municipal/school/hospital races are placed in a companion file:

| Year | Federal/State/County file | Local/School/Hospital file | Notes |
| --- | --- | --- | --- |
| 2020 | `Federal_State_Local_2020.txt` | `Muni_Hospital_School_2020.txt` plus school district summaries | Both files follow the shared schema shown above.【F:2020_Results/Text_File_Layout_2020.txt†L22-L115】 |
| 2022 | `Federal_State_County_Precinct_2022` | `Municipal_Hospital_School_Precinct_2022` | One row per candidate per precinct for all reported offices.【F:2022_Results/Text_File_Layout_2022†L16-L147】 |
| 2024 | `Federal_State_County_ByPrecinct_2024` | `All_MuniHospitalSchoolDistritct_2024` | Federal file includes the presidential race; the local file aggregates municipal, hospital, and school district contests.【F:2024_Results/Federal_State_County_ByPrecinct_2024†L1-L5】【F:2024_Results/All_MuniHospitalSchoolDistritct_2024†L1-L5】 |

Each row contains the county, precinct ID, office, candidate code, and vote totals, so you can aggregate up to any geography by grouping on those fields.  Local races rely heavily on the municipality FIPS or school district identifiers within the `District` column, so join to `mcdtbl.txt` or `School_Districts_*.txt` to display readable names.【F:2024_Results/All_MuniHospitalSchoolDistritct_2024†L1-L5】【F:2020_Results/Text_File_Layout_2020.txt†L24-L39】

### Sample rows
The snippet below (from `Federal_State_County_ByPrecinct_2024`) illustrates the common column order: state code, county, precinct, office, district (blank for statewide races), candidate order code, candidate name, party, precinct reporting counts, votes, and vote share.【F:2024_Results/Federal_State_County_ByPrecinct_2024†L1-L5】  The local example shows how non-partisan school board contests substitute `NP` in the party column and reserve `WI` for write-ins.【F:2024_Results/All_MuniHospitalSchoolDistritct_2024†L1-L5】  Party lookups translate abbreviations such as `WTP` (We the People) and `LIB` (Libertarian) into human-readable labels.【F:2024_Results/Parties_2024†L1-L15】

## Spatial data (2024 only)
The 2024 folder also ships KML boundary files (`mn-cd1-precincts.kml` through `mn-cd8-precincts.kml`) that you can load into GIS tools to map precinct-level returns by congressional district.  These follow the standard KML schema defined by the Open Geospatial Consortium.【F:2024_Results/mn-cd2-precincts.kml†L1-L2】

## Tips for analysis
1. **Normalize identifiers early.** Ingest the lookup tables into relational tables so you can join on county, precinct, municipality, or district IDs when rolling results up to other geographies.
2. **Handle carets in free-text fields.** Replace `^` with `;` if you need the original punctuation for candidate addresses or ballot-question wording.【F:2020_Results/Text_File_Layout_2020.txt†L154-L208】
3. **Aggregate responsibly.** The vote totals already include `Total number of votes for Office in area`, so you can validate your aggregations against that field before publishing derived numbers.【F:2020_Results/Text_File_Layout_2020.txt†L34-L39】
4. **Track reporting progress.** The `Number of Precincts reporting` and `Total number of precincts voting for the office` columns allow you to filter for fully reported races or monitor partial returns on election night.【F:2020_Results/Text_File_Layout_2020.txt†L34-L39】
5. **Use precinct statistics for turnout calculations.** Combine the `pctstats.txt` files with the vote totals to compute turnout as a share of registered voters or total ballots cast.【F:2024_Results/2024_TextFile_Layout†L47-L60】

With these references you can build repeatable pipelines for all three election cycles without hunting through the individual layout PDFs.

## Chatbot interface

To help non-technical users request custom tables or map-ready exports, this repository now includes a lightweight chatbot that understands simple prompts such as "2024 president results in Hennepin County" or "Show me a map for 2024 MN-03".  It streams the semicolon-delimited text files with Python's built-in CSV module, so no pre-ingestion step is required.

### Setup

The command-line chatbot only uses the Python standard library.  Create a virtual environment if you prefer to isolate dependencies.  If you want to expose the FastAPI endpoint, install the optional packages:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Command-line REPL

```bash
python chatbot_cli.py
```

The REPL keeps prompting until you type `quit`.  When you ask for data it aggregates the requested office and returns the top candidates.  When you mention maps, the bot points you to the 2024 precinct KML files (`2024_Results/mn-cd*-precincts.kml`) that you can load into QGIS, Mapbox, or Kepler.gl.

### FastAPI service

Deploy a web-friendly endpoint by running:

```bash
uvicorn chatbot.server:app --reload
```

Send `POST /chat` with a JSON body such as `{ "message": "2024 president results in Ramsey County" }` and the API returns a structured response you can display in any chat UI.  Because the service only depends on the raw text exports and the Python standard library, you can host it anywhere that has access to this repository.

## Predicting the 2026 ballot

Run `python predict_2026_ballot.py` to analyze the 2020–2024 result files, infer which offices follow two-year versus four-year cadences, and write a summary CSV (defaults to `predicted_2026_ballot.csv`).【F:predict_2026_ballot.py†L1-L138】  The script groups by the `OfficeName` column, looks for consistent gaps between the years an office appears (2020, 2022, and/or 2024), and treats midterm-only offices (seen in 2022 but not 2024) as part of the four-year statewide/local rotation that returns in 2026.【F:predict_2026_ballot.py†L17-L109】  Because it now scans the municipal/hospital/school companion files alongside the statewide exports, the prediction list captures city councils, mayors, school boards, and special districts in addition to state/federal offices.【F:predict_2026_ballot.py†L9-L41】

The generated CSV lists every office predicted to appear in 2026, the observed years that informed the cadence, and whether the cadence came from explicit two-year repetition or the midterm heuristic.  Use it as a starting point when deciding which OSS files to pre-aggregate or map ahead of the next general election.【F:predicted_2026_ballot.csv†L1-L25】

## Syncing your local copy to a remote

The repository changes described above live on your local branch.  To publish them to a remote such as GitHub or GitLab:

1. Confirm the working tree is clean (`git status`).  If you have local edits to stage, run `git add` first.
2. Push the current branch to your remote, e.g., `git push origin work` (replace `work` with whatever branch name you use).
3. If collaborators will review the updates, open a pull request after pushing so they can see the new chatbot files, predictor, and README guidance.
