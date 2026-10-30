from scripts.ci_test_report import email_report, read_results


def test_ci_report_reads_junit_and_marks_missing_suites(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "normalizer.xml").write_text(
        """<testsuites><testsuite tests="2" failures="1" errors="0"
        skipped="0" time="0.5">
        <testcase classname="normalizer" name="passes" />
        <testcase classname="normalizer" name="fails">
        <failure message="assertion failed" />
        </testcase></testsuite></testsuites>""",
        encoding="utf-8",
    )

    results = read_results(results_dir, ("normalizer", "voice"))

    assert [(item.name, item.tests, item.failures, item.errors) for item in results] == [
        ("normalizer", 2, 1, 0),
        ("voice", 0, 0, 1),
    ]
    assert "assertion failed" in results[0].details[0]
    assert "No test report" in results[1].details[0]


def test_ci_report_emails_pdf_over_starttls(monkeypatch, tmp_path):
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            calls["ehlo"] = calls.get("ehlo", 0) + 1

        def starttls(self, *, context):
            calls["tls_context"] = context

        def login(self, username, password):
            calls["login"] = (username, password)

        def send_message(self, message):
            calls["message"] = message

    monkeypatch.setattr("scripts.ci_test_report.smtplib.SMTP", FakeSMTP)
    monkeypatch.setenv("CI_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("CI_SMTP_PORT", "")
    monkeypatch.setenv("CI_SMTP_USERNAME", "ci-user")
    monkeypatch.setenv("CI_SMTP_PASSWORD", "ci-password")
    monkeypatch.setenv("CI_SMTP_FROM", "ci@example.test")
    monkeypatch.setenv("CI_EMAIL_TO", "dev@example.test, qa@example.test")
    pdf_path = tmp_path / "test-results.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    email_report(
        pdf_path,
        total_tests=12,
        failures=1,
        errors=0,
        commit="abc123",
    )

    assert calls["connection"] == ("smtp.example.test", 587, 30)
    assert calls["login"] == ("ci-user", "ci-password")
    assert calls["message"]["To"] == "dev@example.test, qa@example.test"
    attachments = list(calls["message"].iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True) == pdf_path.read_bytes()
