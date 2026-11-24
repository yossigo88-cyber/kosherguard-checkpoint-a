# Publication notes

The actual published database artifact is `artifacts/synthetic.sqlite.b64`, a lossless Base64 text encoding. It is present in this repository and is 245,761 bytes. SHA-256: `9e0adf9f12cc60a920d15f34d8599fc489315a8eeff3c31dfafc5638fc12ca85`. No binary .sqlite file is tracked.

Restore from the repository root:

    python -c "import base64,pathlib; p=pathlib.Path('artifacts'); (p/'synthetic.sqlite').write_bytes(base64.b64decode((p/'synthetic.sqlite.b64').read_bytes()))"

The decoded output is a SQLite format 3 database, 184,320 bytes. Its SHA-256 is `4345c70d806d5b91229e9f6c80c4a5ed22ca8959feea5f214c53d7b88ce5098b`. SHA256SUMS verifies actual tracked publication files, including the encoded artifact, without requiring restoration. The decoded file is intentionally not in that publication inventory. `python demo.py` can recreate synthetic demonstration data; no live device data is included.

PROJECT-STRUCTURE.txt lists the actual tracked publication. changed-files.txt records the original Checkpoint A build; the verification correction changes are documented here and in Git history. DEVELOPMENT-FAILURES.md is explicitly reconstructed and sanitized, not a raw historical log.

Setup: Python 3.10+ with the pinned idna dependency in requirements.txt. Run `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`. The suite now has 36 tests: 35 original classifier regressions and one full 28-category policy-fidelity test. Current results are in artifacts/test-results.txt.

Only publication documentation, checksum inventory, verification tests and their results were corrected. Approved policy/source checksum, classifier behavior and database design are unchanged. No Phase 3, real feed, app integration, production change or deployment.
