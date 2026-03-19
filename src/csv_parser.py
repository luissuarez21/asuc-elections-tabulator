# -*- coding: utf-8 -*-
"""
CSV Parser for ASUC Election Data

Handles parsing of election CSV files containing:
- Propositions (Yes/No/Abstain)
- Executive races (IRV - President, EVP, EAVP, AAVP, SAO)
- Senate race (STV - 20 seats)

Per ASUCBL 4105 voting rules

Key CSV characteristics:
- Row 1: Title ("ASUC General Election 2018")
- Row 2: Empty
- Row 3: Column headers
- Row 4+: Ballot data
- Duplicate columns across survey pages (must merge)
- Abstain votes: empty cells (no "Abstain" text in race columns)
- Candidate format: "Name | Party | Description | <heart>"
"""

import pandas as pd
from typing import Dict, List, Optional


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load and validate ASUC election CSV file.

    Args:
        filepath: Path to CSV file

    Returns:
        DataFrame with ballot data

    Note:
        CSV structure: Row 1 = title, Row 2 = empty, Row 3 = headers, Row 4+ = data
    """
    try:
        # Skip first 2 rows (title and empty row), use row 3 as header
        df = pd.read_csv(filepath, skiprows=2, low_memory=False)

        # Verify SubmissionId column exists
        if 'SubmissionId' not in df.columns:
            raise ValueError("CSV missing required 'SubmissionId' column")

        print(f"[OK] Loaded {len(df)} ballots from {filepath}")
        print(f"[OK] Found {len(df.columns)} columns")
        return df

    except Exception as e:
        raise ValueError(f"Error loading CSV: {str(e)}")


def parse_candidate_cell(cell_value: any) -> Optional[Dict[str, any]]:
    """
    Parse candidate string into structured data.

    Args:
        cell_value: Raw cell content from CSV

    Returns:
        Dict with candidate info, or None if empty

    Examples:
        Input: "Alexander Wilfert | Student Action | Senator | <heart>"
        Output: {
            "name": "Alexander Wilfert",
            "party": "Student Action",
            "description": "Senator",
            "wellness_pact": True
        }

        Input: "" or NaN or "Abstain"
        Output: None

    Edge cases handled:
        - Empty cells / NaN
        - Malformed strings (< 2 parts)
        - Unicode heart symbols
        - Inconsistent spacing around pipes
    """
    # Handle empty cells, NaN, or non-string types
    if pd.isna(cell_value) or not isinstance(cell_value, str) or cell_value.strip() == "":
        return None

    cell_value = cell_value.strip()

    # Explicit abstain (shouldn't appear in race columns based on analysis, but handle it)
    if cell_value.lower() == "abstain":
        return None

    # Parse candidate format: "Name | Party | Description | <heart>"
    parts = [p.strip() for p in cell_value.split('|')]

    if len(parts) < 2:
        # Malformed candidate string - log warning but don't crash
        print(f"  [WARNING] Malformed candidate: '{cell_value[:50]}...'")
        return None

    # Check for wellness pact (heart symbol: U+2665, U+2661, U+2764)
    wellness_pact = '\u2665' in cell_value or '\u2661' in cell_value or '\u2764' in cell_value

    # Remove heart symbols from parts if present
    for heart in ['\u2665', '\u2661', '\u2764']:
        parts = [p.replace(heart, '').strip() for p in parts]

    return {
        "name": parts[0].strip(),
        "party": parts[1].strip() if len(parts) > 1 else "",
        "description": parts[2].strip() if len(parts) > 2 else "",
        "wellness_pact": wellness_pact
    }


def coalesce_row_values(row: pd.Series, column_variants: List[str]) -> any:
    """
    Get first non-empty value from duplicate columns in a row.

    Args:
        row: DataFrame row
        column_variants: List of column names to check (e.g., ["col", "col.1", "col.2"])

    Returns:
        First non-empty value, or NaN if all empty
    """
    for col in column_variants:
        if col in row.index:
            val = row[col]
            if pd.notna(val) and val != '':
                return val
    return pd.NA


def extract_race_ballots(df: pd.DataFrame, race_config: Dict[str, any]) -> List[List[Dict]]:
    """
    Extract ranked preferences for a specific race.

    Args:
        df: Election DataFrame
        race_config: Configuration dict with:
            - 'columns': list of base column names (will handle duplicates)
            - 'name': race name for logging

    Returns:
        List of ballots, where each ballot is an ordered list of candidate dicts

    Handles:
        - Duplicate columns across pages (merges them)
        - Skipped ranks (voter ranks 1, 3, 5 but not 2, 4) - compacts ranks
        - Duplicate rankings (same candidate multiple times) - ignores duplicates
        - Empty cells - skips them
        - Malformed candidate strings - logs warning, skips
    """
    ballots = []
    base_columns = race_config['columns']
    race_name = race_config['name']

    # For each base column, find all variants (e.g., "col", "col.1", "col.2")
    column_sets = []
    for base_col in base_columns:
        variants = [col for col in df.columns if col == base_col or col.startswith(base_col + '.')]
        if variants:
            column_sets.append(variants)

    if not column_sets:
        print(f"  [WARNING] No columns found for {race_name}")
        return []

    # Process each ballot (row)
    for idx, row in df.iterrows():
        ballot = []
        seen_candidates = set()  # Track duplicates within this ballot

        # For each ranking position
        for column_variants in column_sets:
            # Get first non-empty value from duplicate columns
            cell_value = coalesce_row_values(row, column_variants)
            candidate = parse_candidate_cell(cell_value)

            if candidate is not None:
                candidate_key = candidate['name'].lower()

                # Skip if already ranked (handle duplicates)
                if candidate_key in seen_candidates:
                    if idx < 10:  # Only log first few to avoid spam
                        print(f"  [WARNING] Ballot {row['SubmissionId']}: duplicate ranking of '{candidate['name']}' in {race_name}")
                    continue

                ballot.append(candidate)
                seen_candidates.add(candidate_key)

        # Only add ballot if it has at least one preference
        # Empty ballots don't count as valid votes per ASUCBL 4105
        if ballot:
            ballots.append(ballot)

    print(f"  [OK] {race_name}: {len(ballots)} valid ballots extracted")
    return ballots


def get_proposition_votes(df: pd.DataFrame, prop_config: Dict[str, str]) -> Dict[str, int]:
    """
    Count Yes/No/Abstain votes for a proposition.

    Args:
        df: Election DataFrame
        prop_config: Dict with 'column' key pointing to base proposition column name

    Returns:
        {"yes": count, "no": count, "abstain": count}

    Note:
        Per ASUCBL 4105 Section 5, majority = Yes > 50% of (Yes + No)
        Abstain votes count toward turnout but not toward passage

    Handles:
        - Duplicate proposition columns across pages (merges them)
        - Case-insensitive matching ("YES", "yes", "Yes")
        - Empty cells treated as abstain
    """
    base_column = prop_config['column']

    # Find all variants of this proposition column
    column_variants = [col for col in df.columns if col == base_column or col.startswith(base_column + '.')]

    if not column_variants:
        print(f"  [WARNING] Proposition column '{base_column}' not found")
        return {"yes": 0, "no": 0, "abstain": 0}

    # Count votes (case-insensitive), merging duplicates
    votes = {"yes": 0, "no": 0, "abstain": 0}

    for idx, row in df.iterrows():
        # Get first non-empty value from duplicate columns
        value = coalesce_row_values(row, column_variants)

        if pd.isna(value) or value == "":
            votes["abstain"] += 1
        else:
            value_lower = str(value).strip().lower()
            if value_lower == "yes":
                votes["yes"] += 1
            elif value_lower == "no":
                votes["no"] += 1
            elif value_lower == "abstain":
                votes["abstain"] += 1
            else:
                # Unknown value - treat as abstain, but log warning
                if idx < 10:  # Only log first few
                    print(f"  [WARNING] Unknown proposition value: '{value}' - treating as abstain")
                votes["abstain"] += 1

    return votes


# ============================================================================
# RACE CONFIGURATION MAPPINGS
# ============================================================================

RACE_CONFIGS = {
    "President": {
        "name": "President",
        "columns": ["President Candidates - 1", "President Candidates - 2",
                   "President Candidates - 3", "President Candidates - 4"],
        "type": "irv"
    },
    "Executive Vice President": {
        "name": "Executive Vice President",
        "columns": ["Executive Vice President - 1", "Executive Vice President - 2",
                   "Executive Vice President Candidates - 1", "Executive Vice President Candidates - 2"],
        "type": "irv"
    },
    "External Affairs Vice President": {
        "name": "External Affairs Vice President",
        "columns": ["External Affairs Vice President Candidates - 1",
                   "External Affairs Vice President Candidates - 2",
                   "External Affairs Vice President Candidates  - 1",  # Note: extra space variant
                   "External Affairs Vice President Candidates  - 2"],
        "type": "irv"
    },
    "Academic Affairs Vice President": {
        "name": "Academic Affairs Vice President",
        "columns": ["Academic Affairs Vice President Candidates - 1",
                   "Academic Affairs Vice President Candidates - 2"],
        "type": "irv"
    },
    "Student Advocate": {
        "name": "Student Advocate",
        "columns": ["Student Advocate Candidates - 1", "Student Advocate Candidates - 2"],
        "type": "irv"
    },
    "Senate": {
        "name": "Senate",
        "columns": [f"Senate Candidates - {i}" for i in range(1, 38)],  # 1-37
        "type": "stv",
        "seats": 20
    }
}

PROPOSITION_CONFIGS = {
    "Proposition 18A": {
        "name": "Proposition 18A Constitutional Amendment",
        "column": "Proposition 18A Constitutional Amendment: The Enrollment Clarification Act"
    },
    "Proposition 18B": {
        "name": "Proposition 18B Student Fee (STARR)",
        "column": "Proposition 18B Student Fee: Student Transformation through Academic Recruitment and Retention (STARR) Referendum"
    }
}


# ============================================================================
# TEST / DEBUG
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "../data/Copy of ElectionResults (2016).csv"

    print("\n" + "="*60)
    print("CSV PARSER TEST")
    print("="*60 + "\n")

    # Load CSV
    df = load_csv(filepath)

    # Test proposition parsing
    print("\n--- PROPOSITIONS ---")
    for prop_id, prop_config in PROPOSITION_CONFIGS.items():
        votes = get_proposition_votes(df, prop_config)
        total = votes['yes'] + votes['no'] + votes['abstain']
        print(f"\n{prop_id}:")
        print(f"  Yes: {votes['yes']} ({100*votes['yes']/total:.1f}%)")
        print(f"  No: {votes['no']} ({100*votes['no']/total:.1f}%)")
        print(f"  Abstain: {votes['abstain']} ({100*votes['abstain']/total:.1f}%)")

    # Test race parsing
    print("\n--- RACES ---")
    for race_id, race_config in RACE_CONFIGS.items():
        ballots = extract_race_ballots(df, race_config)
        if ballots:
            print(f"\n{race_id}:")
            print(f"  Total ballots: {len(ballots)}")
            if len(ballots) > 0:
                sample_ballot = ballots[0]
                print(f"  Sample ballot: {[c['name'] for c in sample_ballot[:3]]}")

                # Count unique candidates
                all_candidates = set()
                for ballot in ballots:
                    for candidate in ballot:
                        all_candidates.add(candidate['name'])
                print(f"  Unique candidates: {len(all_candidates)}")

    print("\n" + "="*60)
    print("PARSING COMPLETE")
    print("="*60 + "\n")
