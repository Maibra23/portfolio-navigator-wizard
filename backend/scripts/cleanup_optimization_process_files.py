#!/usr/bin/env python3
"""
One-time cleanup script for the `optimization-process` branch.

PURPOSE
-------
- Remove test, analysis, and personal utility files that were useful during
  the optimization work but should not be kept in the main repo.
- Remove JSON result artifacts (test outputs, analysis reports).
- Do NOT touch Redis or any live data sources.

SAFETY
------
- Default mode is DRY-RUN (no files are deleted).
- To actually delete files, run explicitly with `--execute`.
- The script prints a simple progress bar as it processes files.

USAGE
-----
  # Dry run (recommended first)
  python backend/scripts/cleanup_optimization_process_files.py

  # Execute deletions
  python backend/scripts/cleanup_optimization_process_files.py --execute

After you have successfully run this script, you should delete this file
from the repository (it is intended as a one-time operational tool).
"""

import argparse
import os
import sys
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# TARGET FILES
# ---------------------------------------------------------------------------

TEST_FILES_TO_REMOVE: List[str] = [
    # One-time / diagnostic test scripts
    "backend/scripts/test_constraint_implementation_validation.py",
    "backend/scripts/test_market_opt_constraints.py",
    "backend/scripts/test_risk_constraint_compliance.py",
    "backend/scripts/test_overlap_periods_and_core_objectives.py",
    "backend/scripts/test_overlap_requirements.py",
    "backend/scripts/test_market_exploration_options.py",
    "backend/scripts/test_diversity_rotation_and_frontiers.py",
    "backend/scripts/test_diversity_rotation_and_optimization.py",
    "backend/scripts/test_overview_tab_metrics.py",
    "backend/scripts/test_portfolio_optimization_changes.py",
    "backend/scripts/test_recommended_reliability_approach.py",
    "backend/scripts/test_seed_variation.py",
    "backend/scripts/test_efficient_frontier_comparison.py",
    "backend/scripts/test_eligible_tickers_analysis.py",
]

ANALYSIS_SCRIPTS_TO_REMOVE: List[str] = [
    "backend/scripts/analyze_portfolio_diversity_improvement.py",
    "backend/scripts/analyze_portfolio_similarity.py",
    "backend/scripts/compare_overlap_selection.py",
    "backend/scripts/verify_optimization_issue.py",
    "backend/scripts/verify_shuffle_works.py",
    "backend/scripts/verify_overlap_approach_all_profiles.py",
]

PERSONAL_UTILITY_FILES_TO_REMOVE: List[str] = [
    # Personal / local tooling, not part of the product
    "delete_old_chat_history.py",
    "extract_chat_history.py",
    "restore_cursor_chat.sh",
    "chat_history_all.json",
    "chat_history_extracted.json",
    "chat_history_readable.txt",
]

JSON_RESULT_FILES_TO_REMOVE: List[str] = [
    # Test & analysis outputs – should not be committed
    "constraint_enforcement_test_results.json",
    "constraint_feasibility_test_results.json",
    "constraint_implementation_validation_results.json",
    "market_exploration_test_results.json",
    "market_opt_constraint_test_results.json",
    "risk_constraint_test_results.json",
    "backend/scripts/test_overlap_results.json",
    "chart_improvements_ranking.json",
    "backend/sector_analysis_report.json",
    "backend/unknown_sector_categorization.json",
]

MISC_FILES_TO_REMOVE: List[str] = [
    # IDE / review / temporary files
    ".cursor/worktrees.json",
    "professional-recommendations.tsx",
]


ALL_TARGETS: List[Tuple[str, str]] = []
for rel in TEST_FILES_TO_REMOVE:
    ALL_TARGETS.append(("test", rel))
for rel in ANALYSIS_SCRIPTS_TO_REMOVE:
    ALL_TARGETS.append(("analysis", rel))
for rel in PERSONAL_UTILITY_FILES_TO_REMOVE:
    ALL_TARGETS.append(("personal", rel))
for rel in JSON_RESULT_FILES_TO_REMOVE:
    ALL_TARGETS.append(("artifact", rel))
for rel in MISC_FILES_TO_REMOVE:
    ALL_TARGETS.append(("misc", rel))


# ---------------------------------------------------------------------------
# PROGRESS BAR UTILITIES
# ---------------------------------------------------------------------------

def print_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """Render a simple text progress bar."""
    if total <= 0:
        return
    width = 30
    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(width * ratio)
    bar = "█" * filled + "·" * (width - filled)
    sys.stdout.write(f"\r{prefix}: [{bar}] {current}/{total}")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# CORE LOGIC
# ---------------------------------------------------------------------------

def resolve_path(rel_path: str) -> str:
    """Resolve repository-relative path to absolute path."""
    return os.path.join(ROOT, "..", rel_path) if not os.path.isabs(rel_path) else rel_path


def collect_existing_targets() -> List[Tuple[str, str, str]]:
    """
    Build a list of (category, rel_path, abs_path) for files that actually exist.
    """
    existing: List[Tuple[str, str, str]] = []
    for category, rel in ALL_TARGETS:
        abs_path = resolve_path(rel)
        if os.path.isfile(abs_path):
            existing.append((category, rel, abs_path))
    return existing


def delete_files(execute: bool = False) -> None:
    existing = collect_existing_targets()
    total = len(existing)

    if total == 0:
        print("No matching files found to clean up. Nothing to do.")
        return

    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"Cleanup mode: {mode}")
    print(f"Repository root: {ROOT}")
    print(f"Found {total} files matching cleanup list.\n")

    deleted = 0
    skipped = 0

    for index, (category, rel, abs_path) in enumerate(existing, start=1):
        print_progress(index, total, prefix="Scanning")
        if execute:
            try:
                os.remove(abs_path)
                deleted += 1
                print(f"\n[DEL] ({category}) {rel}")
            except Exception as exc:
                skipped += 1
                print(f"\n[SKIP] ({category}) {rel} -> {exc}")
        else:
            skipped += 1
            print(f"\n[DRY] ({category}) {rel} -> would delete: {abs_path}")

    print("\nSummary")
    print("-------")
    print(f"Total targets     : {total}")
    print(f"Deleted (execute) : {deleted}")
    print(f"Skipped / dry-run : {skipped}")
    print("\nNOTE: This script is intended as a one-time operational tool for the "
          "`optimization-process` branch. After you have run it and confirmed the "
          "results, you should remove this script from the repository.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time cleanup script for optimization-process branch artifacts."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files instead of performing a dry run.",
    )
    args = parser.parse_args()

    # IMPORTANT: Never touch Redis or any external data stores.
    delete_files(execute=args.execute)


if __name__ == "__main__":
    main()


