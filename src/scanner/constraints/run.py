"""Constraints package entry point."""

from scanner.constraints.evaluate import evaluate_site_constraints, run
from scanner.reporting.generator import generate_deal_sheet

__all__ = ["run", "evaluate_site_constraints"]


def run_pipeline():
    # Run evaluation
    run()
    # Generate report
    generate_deal_sheet()


if __name__ == "__main__":
    run_pipeline()
