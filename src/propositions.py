# -*- coding: utf-8 -*-
"""
Proposition Voting - Simple Majority

Implements simple majority voting for propositions per ASUCBL 4105 Section 5.

Rules:
- Proposition PASSES if: Yes > 50% of (Yes + No)
- Abstain votes count toward turnout but NOT toward passage threshold
- Result is Yes/(Yes+No), NOT Yes/Total
"""

from typing import Dict


def run_proposition(votes: Dict[str, int], prop_name: str) -> Dict:
    """
    Calculate proposition result using simple majority.

    Args:
        votes: Dict with {"yes": count, "no": count, "abstain": count}
        prop_name: Name of proposition for display

    Returns:
        Dict with complete results including:
        {
            "proposition": str,
            "yes_votes": int,
            "no_votes": int,
            "abstain_votes": int,
            "total_turnout": int,
            "yes_percentage": float,  # Of yes+no only
            "result": "PASSED" or "FAILED"
        }

    Per ASUCBL 4105 Section 5:
        Majority = Yes / (Yes + No) > 0.50
        Abstain votes DO NOT count in the denominator
    """
    yes_votes = votes["yes"]
    no_votes = votes["no"]
    abstain_votes = votes["abstain"]

    total_turnout = yes_votes + no_votes + abstain_votes
    deciding_votes = yes_votes + no_votes  # Abstains don't count

    # Calculate percentage of deciding votes (not total turnout)
    if deciding_votes > 0:
        yes_percentage = (yes_votes / deciding_votes) * 100
    else:
        # Edge case: everyone abstained
        yes_percentage = 0.0

    # Passes if yes strictly greater than 50%
    result = "PASSED" if yes_percentage > 50.0 else "FAILED"

    return {
        "proposition": prop_name,
        "yes_votes": yes_votes,
        "no_votes": no_votes,
        "abstain_votes": abstain_votes,
        "total_turnout": total_turnout,
        "deciding_votes": deciding_votes,  # Yes + No
        "yes_percentage": yes_percentage,
        "result": result
    }


def format_proposition_result(result: Dict) -> str:
    """
    Format proposition result for display.

    Args:
        result: Output from run_proposition()

    Returns:
        Formatted string for console output
    """
    prop = result["proposition"]
    yes_v = result["yes_votes"]
    no_v = result["no_votes"]
    abstain_v = result["abstain_votes"]
    total = result["total_turnout"]
    deciding = result["deciding_votes"]
    yes_pct = result["yes_percentage"]
    outcome = result["result"]

    output = []
    output.append(f"\n{'='*60}")
    output.append(f"{prop}")
    output.append(f"{'='*60}")
    output.append(f"Result: {outcome}")
    output.append(f"")
    output.append(f"Vote Breakdown:")
    output.append(f"  Yes:     {yes_v:>6} ({yes_pct:.1f}% of deciding votes)")
    output.append(f"  No:      {no_v:>6}")
    output.append(f"  Abstain: {abstain_v:>6}")
    output.append(f"")
    output.append(f"Total Turnout:   {total:>6}")
    output.append(f"Deciding Votes:  {deciding:>6} (Yes + No)")
    output.append(f"")
    output.append(f"Threshold: >50% of deciding votes needed to pass")

    return "\n".join(output)


# ============================================================================
# TEST / DEBUG
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROPOSITION VOTING TEST")
    print("="*60)

    # Test case 1: Clear pass
    print("\n--- Test 1: Clear Majority Pass ---")
    test1 = {"yes": 700, "no": 300, "abstain": 200}
    result1 = run_proposition(test1, "Test Prop 1 - Should Pass")
    print(format_proposition_result(result1))
    assert result1["result"] == "PASSED"
    assert result1["yes_percentage"] == 70.0

    # Test case 2: Clear fail
    print("\n--- Test 2: Clear Majority Fail ---")
    test2 = {"yes": 300, "no": 700, "abstain": 200}
    result2 = run_proposition(test2, "Test Prop 2 - Should Fail")
    print(format_proposition_result(result2))
    assert result2["result"] == "FAILED"

    # Test case 3: Exactly 50% (should fail - needs >50%)
    print("\n--- Test 3: Exactly 50% (Edge Case) ---")
    test3 = {"yes": 500, "no": 500, "abstain": 100}
    result3 = run_proposition(test3, "Test Prop 3 - Tie")
    print(format_proposition_result(result3))
    assert result3["result"] == "FAILED"
    assert result3["yes_percentage"] == 50.0

    # Test case 4: Barely passes (50.1%)
    print("\n--- Test 4: Barely Passes (50.1%) ---")
    test4 = {"yes": 501, "no": 499, "abstain": 1000}
    result4 = run_proposition(test4, "Test Prop 4 - Narrow Pass")
    print(format_proposition_result(result4))
    assert result4["result"] == "PASSED"

    # Test case 5: Most people abstain
    print("\n--- Test 5: High Abstain Rate ---")
    test5 = {"yes": 100, "no": 50, "abstain": 10000}
    result5 = run_proposition(test5, "Test Prop 5 - High Abstain")
    print(format_proposition_result(result5))
    assert result5["result"] == "PASSED"
    assert abs(result5["yes_percentage"] - 66.67) < 0.1

    print("\n" + "="*60)
    print("ALL PROPOSITION TESTS PASSED!")
    print("="*60 + "\n")
