# Sanitized development-failure summary

This is a reconstructed summary, not a preserved raw failing-run transcript. The original failing-output file was overwritten by later successful test runs. No internal conversation or execution transcript is published.

Initial development run: 30 tests, 24 errors, 0 assertion failures. The 24 errors shared one cause: the release insert supplied 7 SQL placeholders for a 6-column releases table. Fixed the placeholder count. A separate policy-category placeholder mismatch was caught and corrected before this first run.

The initial run also emitted one ResourceWarning because the negative network test created a socket without closing it. The test was changed to use a socket context manager. The blocked socket connection itself behaved as expected.

After these fixes: 30/30 tests passed. Five additional safety tests were added, and the final complete run passed 35/35 with no errors, failures or warnings. The exact final transcript is artifacts/test-results.txt. No real dataset, live device, production system or network request was used in these tests.

These failures were implementation defects in the synthetic prototype, not results of real-world domain classification. No test establishes production accuracy, capacity or enforcement readiness.
