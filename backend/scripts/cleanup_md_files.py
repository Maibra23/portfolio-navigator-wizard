#!/usr/bin/env python3
"""
One-time script to remove redundant/temporary markdown documentation files.

This script removes:
- Implementation summaries (one-time documentation)
- Design mockups (now implemented)
- Test/diagnosis results (one-time)
- Redundant explanations (consolidated into OPTIMIZATION_WORKFLOW_AND_RECOMMENDATIONS.md)
- Review documents (one-time)

Run with --execute to actually delete files, otherwise shows what would be deleted.
"""

import os
import sys
import argparse
from pathlib import Path

# Files to remove (relative to repository root)
FILES_TO_REMOVE = [
    # Implementation summaries (one-time)
    "BOX_ZOOM_FIX_SUMMARY.md",
    "CHART_IMPLEMENTATION_SUMMARY.md",
    "CHART_IMPROVEMENTS_IMPLEMENTED.md",
    "OPTIMIZATION_BUTTON_CHANGES_SUMMARY.md",
    "OPTIMIZATION_WORKFLOW_CHANGES.md",
    "IMPLEMENTATION_SUMMARY.md",
    "OPTION_3_IMPLEMENTATION_PLAN.md",
    "backend/IMPLEMENTATION_PLAN_SHARPE_MINIMIZATION.md",
    
    # Design mockups (now implemented)
    "THREE_COLUMN_COMPARISON_DESIGN.md",
    "VISUAL_MOCKUP_THREE_COLUMN.md",
    
    # Test/diagnosis results (one-time)
    "DIAGNOSIS_SUMMARY.md",
    "OPTIMIZATION_TEST_RESULTS.md",
    "RELIABILITY_TEST_RESULTS.md",
    "RELIABILITY_TEST_RESULTS_V2.md",
    "VERIFICATION_RESULTS_ALL_PROFILES.md",
    
    # Redundant explanations (consolidated)
    "ANALYTICS_EXPLANATIONS.md",
    "CML_AND_CHARTS_EXPLANATION.md",
    "CML_AND_EFFICIENT_FRONTIER_EXPLANATION.md",
    "OPTIMIZATION_AND_ANALYTICS_EXPLANATION.md",
    "ELIGIBLE_TICKERS_AND_DUAL_OPTIMIZATION_EXPLANATION.md",
    "CHART_VISUALIZATION_EXPLANATION.md",
    "FINANCIAL_VISUALIZATION.md",
    
    # Redundant decision framework
    "MARKET_EXPLORATION_DECISION_FRAMEWORK.md",
    
    # Review documents (one-time)
    "BRANCH_REVIEW_RECOMMENDATIONS.md",
    "frontend/src/components/wizard/EFFICIENT_FRONTIER_REVIEW.md",
]

def get_repo_root():
    """Get repository root directory."""
    script_dir = Path(__file__).parent
    # Go up from backend/scripts to repo root
    repo_root = script_dir.parent.parent
    return repo_root

def print_progress(current, total, prefix="Progress"):
    """Print progress bar."""
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "█" * filled + "·" * (bar_length - filled)
    percent = (current / total) * 100
    print(f"\r{prefix}: [{bar}] {current}/{total} ({percent:.0f}%)", end="", flush=True)
    if current == total:
        print()  # New line when complete

def main():
    parser = argparse.ArgumentParser(
        description="Remove redundant/temporary markdown documentation files"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (default is dry-run)"
    )
    args = parser.parse_args()
    
    repo_root = get_repo_root()
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    
    print("=" * 80)
    print(f"Markdown Files Cleanup - {mode}")
    print("=" * 80)
    print(f"Repository root: {repo_root}")
    print()
    
    # Find files that exist
    existing_files = []
    for file_path in FILES_TO_REMOVE:
        full_path = repo_root / file_path
        if full_path.exists():
            existing_files.append(full_path)
        else:
            print(f"[SKIP] File not found: {file_path}")
    
    if not existing_files:
        print("No files found to remove.")
        return
    
    print(f"Found {len(existing_files)} files matching cleanup list.")
    print()
    
    # Categorize files
    categories = {
        "implementation": [],
        "design": [],
        "test": [],
        "redundant": [],
        "review": []
    }
    
    for file_path in existing_files:
        filename = file_path.name
        if "IMPLEMENTATION" in filename or "SUMMARY" in filename or "CHANGES" in filename or "PLAN" in filename:
            categories["implementation"].append(file_path)
        elif "DESIGN" in filename or "MOCKUP" in filename:
            categories["design"].append(file_path)
        elif "TEST" in filename or "RESULTS" in filename or "DIAGNOSIS" in filename or "VERIFICATION" in filename:
            categories["test"].append(file_path)
        elif "EXPLANATION" in filename or "ANALYTICS" in filename or "CML" in filename or "CHART" in filename or "FINANCIAL" in filename or "DECISION" in filename:
            categories["redundant"].append(file_path)
        else:
            categories["review"].append(file_path)
    
    # Process files
    deleted_count = 0
    skipped_count = 0
    
    print("Processing files...")
    print()
    
    for i, file_path in enumerate(existing_files, 1):
        print_progress(i, len(existing_files), "Scanning")
        
        try:
            relative_path = file_path.relative_to(repo_root)
            
            # Determine category for display
            cat = "misc"
            for category, files in categories.items():
                if file_path in files:
                    cat = category
                    break
            
            if args.execute:
                file_path.unlink()
                print(f"\r[DEL] ({cat:12}) {relative_path}")
                deleted_count += 1
            else:
                print(f"\r[WOULD DELETE] ({cat:12}) {relative_path}")
                deleted_count += 1
                
        except Exception as e:
            print(f"\r[ERROR] Failed to process {file_path}: {e}")
            skipped_count += 1
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total targets     : {len(existing_files)}")
    print(f"{'Deleted' if args.execute else 'Would delete'}: {deleted_count}")
    print(f"Skipped / errors  : {skipped_count}")
    print()
    
    if not args.execute:
        print("NOTE: This was a dry-run. No files were deleted.")
        print("Run with --execute to actually delete files.")
    else:
        print("✅ Cleanup complete!")
        print()
        print("NOTE: This script is intended as a one-time operational tool.")
        print("After you have confirmed the results, you should remove this script.")
    
    print()

if __name__ == "__main__":
    main()

