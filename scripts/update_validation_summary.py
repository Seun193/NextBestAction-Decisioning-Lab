from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def junit_total(path: Path) -> int:
    root = ET.parse(path).getroot()

    tests = root.attrib.get("tests")
    if tests is not None:
        return int(tests)

    suites = list(root.findall(".//testsuite"))
    if not suites:
        raise ValueError(f"No tests/testsuites found in {path}")

    leaf_suites = [suite for suite in suites if not suite.findall("testsuite")]
    return sum(int(suite.attrib.get("tests", "0")) for suite in leaf_suites)


def replace_required(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"Could not update README section: {label}")
    return updated


def update_readme(readme: Path, smoke_count: int, regression_count: int) -> bool:
    original = readme.read_text(encoding="utf-8")
    text = original

    text = replace_required(
        text,
        r"(## Current Validation Baseline\s+\*\*)\d+(\s+automated tests passing\*\*)",
        rf"\g<1>{regression_count}\g<2>",
        "Current Validation Baseline",
    )

    text = replace_required(
        text,
        r"(Latest validated release result:\s+```text\s+"
        r"Stage 1 - Release Readiness Smoke Validation\s+)\d+(\s+passed\s+"
        r"Stage 2 - Complete Regression Validation\s+)\d+(\s+passed)",
        rf"\g<1>{smoke_count}\g<2>{regression_count}\g<3>",
        "Current Validation Baseline release summary",
    )

    text = replace_required(
        text,
        r"(## Automated Testing.*?Current validated baseline:\s+```text\s+)\d+(\s+passed)",
        rf"\g<1>{regression_count}\g<2>",
        "Automated Testing baseline",
    )

    text = replace_required(
        text,
        r"(## Release Readiness Validation.*?"
        r"### Stage 1 .*?Latest validated result:\s+```text\s+)\d+(\s+passed)",
        rf"\g<1>{smoke_count}\g<2>",
        "Release Readiness Stage 1",
    )

    text = replace_required(
        text,
        r"(## Release Readiness Validation.*?"
        r"### Stage 2 .*?Latest validated result:\s+```text\s+)\d+(\s+passed)",
        rf"\g<1>{regression_count}\g<2>",
        "Release Readiness Stage 2",
    )

    if text == original:
        return False

    readme.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update README validation counts from pytest JUnit reports."
    )
    parser.add_argument("--smoke-report", required=True, type=Path)
    parser.add_argument("--regression-report", required=True, type=Path)
    parser.add_argument("--readme", default=Path("README.md"), type=Path)
    args = parser.parse_args()

    try:
        smoke_count = junit_total(args.smoke_report)
        regression_count = junit_total(args.regression_report)

        changed = update_readme(
            args.readme,
            smoke_count=smoke_count,
            regression_count=regression_count,
        )
    except Exception as exc:
        print(f"Validation summary update failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validation summary: smoke={smoke_count}, regression={regression_count}")

    if changed:
        print(f"Updated {args.readme}")
    else:
        print(f"{args.readme} already current")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
