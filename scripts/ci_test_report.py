"""Create a PDF summary from pytest JUnit XML and optionally email it."""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SuiteResult:
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    duration: float
    details: tuple[str, ...]

    @property
    def passed(self) -> int:
        return max(0, self.tests - self.failures - self.errors - self.skipped)


def _suite_nodes(root: ET.Element) -> Iterable[ET.Element]:
    if root.tag == "testsuite":
        yield root
    else:
        yield from root.iter("testsuite")


def read_results(
    results_dir: Path, expected_suites: tuple[str, ...] = ()
) -> list[SuiteResult]:
    results = []
    for report in sorted(results_dir.rglob("*.xml")):
        root = ET.parse(report).getroot()
        nodes = list(_suite_nodes(root))
        if not nodes:
            results.append(
                SuiteResult(
                    name=report.stem,
                    tests=0,
                    failures=0,
                    errors=1,
                    skipped=0,
                    duration=0,
                    details=("ERROR: JUnit report contains no test suites",),
                )
            )
            continue

        tests = failures = errors = skipped = 0
        duration = 0.0
        details = []
        for node in nodes:
            node_failures = node_errors = node_skipped = 0
            for case in node.findall("testcase"):
                name = f"{case.get('classname', '')}.{case.get('name', 'unknown')}".strip(".")
                failure = case.find("failure")
                error = case.find("error")
                skip = case.find("skipped")
                if failure is not None:
                    node_failures += 1
                    details.append(f"FAIL: {name} - {failure.get('message', '')}")
                elif error is not None:
                    node_errors += 1
                    details.append(f"ERROR: {name} - {error.get('message', '')}")
                elif skip is not None:
                    node_skipped += 1
            tests += int(node.get("tests", "0"))
            failures += int(node.get("failures", str(node_failures)))
            errors += int(node.get("errors", str(node_errors)))
            skipped += int(node.get("skipped", str(node_skipped)))
            duration += float(node.get("time", "0"))
        results.append(
            SuiteResult(
                name=report.stem,
                tests=tests,
                failures=failures,
                errors=errors,
                skipped=skipped,
                duration=duration,
                details=tuple(details),
            )
        )

    reported = {result.name for result in results}
    for expected in expected_suites:
        if expected not in reported:
            results.append(
                SuiteResult(
                    name=expected,
                    tests=0,
                    failures=0,
                    errors=1,
                    skipped=0,
                    duration=0,
                    details=(f"ERROR: No test report was produced for {expected}",),
                )
            )
    return results


def create_pdf(results: list[SuiteResult], output: Path, commit: str) -> tuple[int, int, int]:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    total_tests = sum(item.tests for item in results)
    total_failures = sum(item.failures for item in results)
    total_errors = sum(item.errors for item in results)
    total_skipped = sum(item.skipped for item in results)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#183153"),
    )
    detail_style = ParagraphStyle(
        "FailureDetail",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )
    document = SimpleDocTemplate(
        str(output),
        pagesize=landscape(A4),
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="MIM-AI CI Test Results",
        author="MIM-AI CI",
    )
    story = [
        Paragraph("MIM-AI CI Test Results", title_style),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
            f"| Commit: {escape(commit or 'unknown')}",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
    ]

    if not results:
        story.append(Paragraph("No JUnit test reports were available.", styles["Heading2"]))
    else:
        story.append(
            Paragraph(
                f"Total: {total_tests} tests | "
                f"Passed: {total_tests - total_failures - total_errors - total_skipped} | "
                f"Failed: {total_failures} | Errors: {total_errors} | "
                f"Skipped: {total_skipped}",
                styles["Heading2"],
            )
        )
        story.append(
            Paragraph(
                "Model-dependent Presidio integration tests are excluded from CI; "
                "anonymizer configuration and operator tests still run.",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 3 * mm))
        rows = [["Test suite", "Tests", "Passed", "Failures", "Errors", "Skipped", "Time (s)"]]
        for result in results:
            rows.append(
                [
                    result.name,
                    str(result.tests),
                    str(result.passed),
                    str(result.failures),
                    str(result.errors),
                    str(result.skipped),
                    f"{result.duration:.2f}",
                ]
            )
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183153")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F9")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D0DB")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([table, Spacer(1, 5 * mm)])
        details = [detail for result in results for detail in result.details]
        if details:
            story.append(Paragraph("Failure details", styles["Heading2"]))
            for detail in details:
                story.append(Paragraph(escape(detail), detail_style))
                story.append(Spacer(1, 1 * mm))

    document.build(story)
    return total_tests, total_failures, total_errors


def email_report(
    output: Path,
    *,
    total_tests: int,
    failures: int,
    errors: int,
    commit: str,
) -> None:
    host = os.environ.get("CI_SMTP_HOST")
    sender = os.environ.get("CI_SMTP_FROM")
    recipients = [
        address.strip()
        for address in os.environ.get("CI_EMAIL_TO", "").split(",")
        if address.strip()
    ]
    if not host or not sender or not recipients:
        raise ValueError(
            "Email requires CI_SMTP_HOST, CI_SMTP_FROM, and at least one CI_EMAIL_TO recipient"
        )

    username = os.environ.get("CI_SMTP_USERNAME")
    password = os.environ.get("CI_SMTP_PASSWORD")
    if bool(username) != bool(password):
        raise ValueError("Set both CI_SMTP_USERNAME and CI_SMTP_PASSWORD, or neither")

    port = int(os.environ.get("CI_SMTP_PORT") or "587")
    message = EmailMessage()
    status = "PASSED" if failures == 0 and errors == 0 else "FAILED"
    message["Subject"] = f"[mim-ai CI] {status}: {total_tests} tests"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(
        f"CI test status: {status}\n"
        f"Tests: {total_tests}\nFailures: {failures}\nErrors: {errors}\n"
        f"Commit: {commit or 'unknown'}\n\n"
        "The detailed PDF test report is attached."
    )
    message.add_attachment(
        output.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=output.name,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        if username:
            server.login(username, password or "")
        server.send_message(message)
    print(f"Sent PDF test report to {', '.join(recipients)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="")
    parser.add_argument("--expected-suites", nargs="*", default=[])
    parser.add_argument("--email", action="store_true")
    args = parser.parse_args()

    results = read_results(args.results_dir, tuple(args.expected_suites))
    total_tests, failures, errors = create_pdf(results, args.output, args.commit)
    print(
        f"Created {args.output}: {total_tests} tests, "
        f"{failures} failures, {errors} errors across {len(results)} suites"
    )
    if args.email:
        email_report(
            args.output,
            total_tests=total_tests,
            failures=failures,
            errors=errors,
            commit=args.commit,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
