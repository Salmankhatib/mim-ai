# Open issues and known limitations

This file tracks current limitations only. Completed or disproven findings from
older audits are intentionally not repeated here.

## Known limitations

- **Anonymizer language coverage:** The packaged Presidio analyzer supports
  English only and requires its spaCy model. Moroccan CIN and phone regex
  recognizers are included, but they do not provide French or Darija NER.
- **Custom audit adapters:** To verify a chain, an adapter must implement
  `iter_chain_records()` and return records in append order. Multi-writer chain
  writes additionally require atomic `append_chained()`.
- **Audit erasure and retention:** Removing chain entries can make the retained
  history unverifiable. Verification checks the links present in storage; it
  cannot prove the authenticity of entries that were deleted.
- **External service validation:** PostgreSQL, MySQL, and MongoDB readers are
  implemented but require their respective optional driver and a live service
  for end-to-end integration testing.

## Verified behavior

- `load_config()` reads an explicitly named file and does not create config
  files or discover legacy filenames. `mim-init` remains the explicit setup
  command.
- Voice's empty-chat response is configurable as `voice.fallback_response`.
- Presidio `encrypt` configuration is validated before use and supports an
  environment-variable reference for its key.
- Built-in SQLite, JSONL, PostgreSQL, MySQL, and MongoDB audit stores expose
  ordered records for chain verification.
