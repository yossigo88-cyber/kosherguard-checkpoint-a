# Publication notes

All original tested text files are byte-for-byte unchanged. The synthetic database is provided as artifacts/synthetic.sqlite.b64, a lossless Base64 text encoding, because the browser upload route changed binary filenames. Restore it locally from this repository root with:

    python -c "import base64,pathlib; p=pathlib.Path('artifacts'); (p/'synthetic.sqlite').write_bytes(base64.b64decode((p/'synthetic.sqlite.b64').read_bytes()))"

Then `sha256sum -c SHA256SUMS` checks all original package files, including the restored binary. Alternatively, `python demo.py` recreates a synthetic demonstration database. No real device data is present.

PROJECT-STRUCTURE.txt lists the original project plus the development-failure report. This publication additionally contains this note and the encoded database. The final test log and original changed-file list are unchanged. DEVELOPMENT-FAILURES.md is explicitly reconstructed and sanitized, not a raw historical transcript.

Setup in a local Python 3.10+ environment: install the pinned idna dependency from requirements.txt if absent, then run `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`. The publication was checked by anonymous clone and all 35 tests passed. No Phase 3 work, real feed downloads, app integration, production change or deployment is included.
