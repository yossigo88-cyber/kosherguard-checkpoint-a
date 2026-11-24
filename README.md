# KosherGuard Checkpoint A

Phases 0-2 only. Synthetic-only isolated development prototype, completed November 23, 2026. Not a production release. Phase 3 is not authorized and has not started.

## Contents and run

- `docs/build-contract.md`: frozen scope, versions, matching contract, gates and limitations.
- `docs/approved-policy-v1.0.ts`: unchanged approved policy definitions.
- `docs/policy-sha256.txt`: original policy checksum.
- `fixtures/policy-v1.0.json`: faithful structured copy of all 28 categories and stable IDs.
- `src/schema.sql`: constrained synthetic SQLite schema.
- `src/classifier.py`: synthetic store helper and deterministic read-only classifier.
- `tests/test_classifier.py`: 35 regression tests.
- `demo.py`: creates only `artifacts/synthetic.sqlite` and JSON demonstrations.
- `artifacts/`: test transcript, synthetic database, integrity report and demo results.
- `requirements.txt`: existing dependency version recorded, not installed/downloaded.
- `SHA256SUMS`: artifact/source integrity inventory.

Run from this directory in a Python environment with the recorded dependency already available:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
    PYTHONDONTWRITEBYTECODE=1 python demo.py

Tested locally with Python 3.10.12, SQLite 3.37.2 and existing idna 3.3. No dependency installation or download took place. This is a Python reference prototype rather than an integration into the Node dashboard. Future runtime/driver selection remains gated before app integration.

There is no listener, network client, downloader, feed importer, app adapter, proxy, DNS service or MDM connection. Phone/profile adapter doubles raise immediately. Tests deny socket connections. Disk database paths are restricted to this directory's artifacts folder. No real devices or settings are read. Fixture settings are caller-owned complete dictionaries; incomplete/ambiguous values raise for review rather than silently defaulting OFF.

The suite tests algorithm behavior, not real-site policy accuracy. Exclusion-domain examples are unknown synthetic hosts, not evidence of automatic semantic classification. There is no real PSL, live source/license clearance, real feed, production deployment or filtering activation. No production capacity claim follows from these tiny fixtures.

Known issues found during development: SQL placeholder count mismatches and an unclosed test socket. Both were fixed before the final 35/35 passing run. No remaining failing test. See build-contract limitations before considering further work.
