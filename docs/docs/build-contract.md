# Frozen build contract: Checkpoint A, version A.1

## Scope

Only isolated synthetic development Phases 0, 1 and 2. No live feeds, production DB/server/app/MDM changes, phone commands, device-setting writes, deployment, activation or paid service. Stop after Phase 2. Rollback is deletion of this isolated directory, not restoration of any live system.

Policy reference: Category Policy v1.0, all 28 definitions unchanged. The source checksum is in policy-sha256.txt. Structured policy data retains definitions, inclusions, exclusions and rules. Stable category IDs map to the existing 28 keys without changing app code.

## Model and versions

SQLite tables separate policy/categories, license evidence, snapshots, host rules, inactive URL rules, raw assertions, reviewed assignments, corrections, review queue and release membership. Approved decisions/corrections are append-only. A revoke/replace names a prior decision; competing successors are rejected for review. This is a trusted synthetic test API, not an authenticated production approval UI. Synthetic reviewer/evidence/timestamps do not represent human approval of actual domains.

Constants: policy 1.0, parser-1, synthetic-psl-1. Releases have explicit IDs, immutable membership and SHA-256 manifest hashes. Effective classifications and corrections carry approving policy versions. The current correction sequence is a conservative count of immutable review decisions, so unrelated reviews also invalidate caches. Release-time sequence and evaluation-time current sequence are separate: rolling feed membership back cannot undo newer corrections. No active-release pointer or production publisher is implemented in this phase.

## Matching and errors

Input is a hostname, not a URL/port/IP. Strict IDNA2008 via idna 3.3; NFC, lowercase and one trailing dot canonicalize. Reject malformed labels, URL delimiters, wildcards, IP literals and ambiguous numeric hosts. IP classification is unsupported. Unicode confusable names are not treated as aliases.

Synthetic PSL implements exact, wildcard and exception matching and private shared-host fixtures. Suffix-wide rules are rejected. This intentionally tiny PSL is not suitable for internet use. Real PSL retrieval/version/provenance validation needs separate permission. A PSL-version mismatch stops classification for review; it never broadens old rules.

EXACT_HOST is default. Descendant scope requires an explicit approved fixture rule, matching DNS label boundaries. Raw assertions do not enter release membership. Normalization cannot turn URL rules into hostname rules. All URL rules are constrained unsupported/inactive here, regardless of exact/prefix metadata. No URL matching or TLS inspection is claimed.

Same-category suppression applies at the same or a more-specific hostname than the approved inherited assignment, only where the correction scope matches the query. Exact suppression does not affect its children. Descendant suppression affects children, not sibling lookalikes. Other categories remain. Repeated/new-source evidence is queued and cannot override a correction by changing IDs. A separately approved more-specific assignment conflicting with a broader suppression raises ReviewRequired, not an invented precedence outcome. Replacing a correction is an explicit audited revoke plus new suppression in one transaction. Later approval-workflow design needs its own review.

Classification produces categories, blocking-category intersection, explanation IDs/versions, suppressed-assignment details and enforcement=false. UNKNOWN is distinct from SUPPRESSED and CLASSIFIED. Invalid input/missing releases raise errors; incomplete settings, conflicting approval or policy/PSL mismatches raise ReviewRequired. These are not fail-open/fail-closed decisions. Unknown/outage behavior remains undecided and unenforced.

## Safety, acceptance and gates

Lookup is read-only; tested with SQLite denying writes. It queries only suffix-ancestor host candidates through an index, not every hostname. Cache maximum is bounded (default 32), includes normalized host, policy, release, correction sequence, caller selection version and full explicit settings, and returns defensive copies. This establishes deterministic correctness on fixtures, not production performance.

A release is assembled inside a transaction; rollback removes uncommitted membership. Persistence/reopen and selecting older releases keep current approved corrections. Tests use memory or databases restricted under artifacts; no credentials, live settings or production paths are included. All 28 fixture flags are tested; missing legacy values are never filled automatically.

Checkpoint A acceptance: all synthetic regressions pass, policy checksum unchanged, SQLite integrity and foreign keys pass, source inventory complete, forbidden adapters raise, no real resources touched. Current test count is 35. No numerical production precision/recall/latency/RAM thresholds are agreed. Those must be approved before later scale gates; Checkpoint A does not authorize such tests.

Before Phase 3: explicit user approval; exact source/license and intended-storage clearance; permitted snapshot/category subset; classification review criteria. Before app/server work: separate integration/deployment permission, fresh resource baseline, backup/rollback rehearsal and agreed abort thresholds. Before any real phone test: explicit named-device exception to the phone-command ban. Activation requires independent permission. 1GB suitability, real-site coverage, security approval/authentication, production locking/concurrency, source freshness, license compatibility and device recovery remain unproven.
