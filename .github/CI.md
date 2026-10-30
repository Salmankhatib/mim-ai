# CI and test-result reports

The GitHub Actions workflow runs Ruff and a separate pytest job for each test
area: normalizer, chatbot/intents, voice, audit, anonymizer, and SDK/examples.
The reporting utility also has its own focused tests.
It also runs the full test suite on Python 3.9, 3.10, and 3.11; the module jobs
run on Python 3.12. Tests that require the separately downloaded spaCy English
model are marked `requires_spacy` and excluded from CI to avoid the large model
download; anonymizer configuration, operator, and language-validation tests
still run. To include model-dependent tests locally, install the model and run
pytest without the marker exclusion.
The workflow builds a PDF summary from the JUnit XML reports and retains it as
the `test-results-pdf` artifact for 30 days.

## Optional email delivery

Email is disabled unless the GitHub Actions run is on the default branch (or
manually dispatched) and these repository or environment secrets are configured:

- `CI_SMTP_HOST` — SMTP server hostname
- `CI_SMTP_FROM` — sender address
- `CI_EMAIL_TO` — recipient address or comma-separated recipient list
- `CI_SMTP_PORT` — optional; defaults to `587` and uses STARTTLS
- `CI_SMTP_USERNAME` and `CI_SMTP_PASSWORD` — optional SMTP authentication;
  configure both or neither

The generated PDF is attached to the email. Credentials are read only from
Actions secrets; do not put SMTP credentials or recipient tokens in workflow
files. Email delivery runs in the report job and can fail independently of the
test jobs if the configured SMTP server is unavailable.
