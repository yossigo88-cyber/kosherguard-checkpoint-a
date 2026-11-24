PRAGMA foreign_keys=ON;
CREATE TABLE policy_versions(version TEXT PRIMARY KEY, content_hash TEXT NOT NULL);
CREATE TABLE categories(id TEXT PRIMARY KEY, ordinal INTEGER UNIQUE NOT NULL CHECK(ordinal BETWEEN 1 AND 28), name TEXT NOT NULL);
CREATE TABLE policy_categories(policy TEXT REFERENCES policy_versions(version), category TEXT REFERENCES categories(id), definition TEXT NOT NULL, inclusions TEXT NOT NULL, exclusions TEXT NOT NULL, rules TEXT NOT NULL, PRIMARY KEY(policy,category));
CREATE TABLE sources(id TEXT PRIMARY KEY, license_state TEXT NOT NULL CHECK(license_state IN ('synthetic','unresolved','cleared')), evidence TEXT NOT NULL);
CREATE TABLE license_evidence(id TEXT PRIMARY KEY,source TEXT NOT NULL REFERENCES sources(id),hash TEXT NOT NULL,notices TEXT NOT NULL,intended_use TEXT NOT NULL);
CREATE TABLE snapshots(id TEXT PRIMARY KEY, source TEXT NOT NULL REFERENCES sources(id), content_hash TEXT NOT NULL, parser_version TEXT NOT NULL, synthetic INTEGER NOT NULL CHECK(synthetic=1));
CREATE TABLE hostname_rules(id INTEGER PRIMARY KEY, host TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('EXACT_HOST','HOST_AND_DESCENDANTS')), psl_version TEXT NOT NULL, UNIQUE(host,scope));
CREATE TABLE url_rules(id TEXT PRIMARY KEY, url TEXT NOT NULL, semantics TEXT NOT NULL CHECK(semantics IN ('EXACT','PREFIX')), supported INTEGER NOT NULL DEFAULT 0 CHECK(supported=0), active INTEGER NOT NULL DEFAULT 0 CHECK(active=0));
CREATE TABLE source_assertions(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL REFERENCES snapshots(id), rule INTEGER NOT NULL REFERENCES hostname_rules(id), category TEXT NOT NULL REFERENCES categories(id), evidence TEXT NOT NULL);
CREATE TABLE review_decisions(id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('APPROVE','SUPPRESS','REVOKE','REPLACE')), policy TEXT NOT NULL REFERENCES policy_versions(version), reviewer TEXT NOT NULL CHECK(length(reviewer)>0), evidence TEXT NOT NULL CHECK(length(evidence)>0), decided_at TEXT NOT NULL, supersedes TEXT REFERENCES review_decisions(id));
CREATE TABLE effective_assignments(id TEXT PRIMARY KEY, rule INTEGER NOT NULL REFERENCES hostname_rules(id), category TEXT NOT NULL REFERENCES categories(id), assertion TEXT NOT NULL REFERENCES source_assertions(id), decision TEXT NOT NULL REFERENCES review_decisions(id), policy TEXT NOT NULL REFERENCES policy_versions(version));
CREATE TABLE corrections(id TEXT PRIMARY KEY, rule INTEGER NOT NULL REFERENCES hostname_rules(id), category TEXT NOT NULL REFERENCES categories(id), decision TEXT NOT NULL REFERENCES review_decisions(id), policy TEXT NOT NULL REFERENCES policy_versions(version));
CREATE TABLE review_queue(id INTEGER PRIMARY KEY, assertion TEXT REFERENCES source_assertions(id), reason TEXT NOT NULL, UNIQUE(assertion,reason));
CREATE TABLE releases(id TEXT PRIMARY KEY, policy TEXT NOT NULL REFERENCES policy_versions(version), correction_version INTEGER NOT NULL CHECK(correction_version>=0), psl_version TEXT NOT NULL, parser_version TEXT NOT NULL, manifest_hash TEXT NOT NULL);
CREATE TABLE release_assignments(release TEXT REFERENCES releases(id), assignment TEXT REFERENCES effective_assignments(id), PRIMARY KEY(release,assignment));
CREATE INDEX hostname_lookup ON hostname_rules(host);
CREATE INDEX assignments_rule ON effective_assignments(rule,category);
CREATE INDEX corrections_rule ON corrections(rule,category);
CREATE TRIGGER assignment_approval BEFORE INSERT ON effective_assignments BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM review_decisions d JOIN source_assertions a ON a.id=NEW.assertion WHERE d.id=NEW.decision AND d.kind='APPROVE' AND d.policy=NEW.policy AND a.rule=NEW.rule AND a.category=NEW.category) THEN RAISE(ABORT,'assignment approval mismatch') END;
END;
CREATE TRIGGER correction_approval BEFORE INSERT ON corrections BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM review_decisions WHERE id=NEW.decision AND kind='SUPPRESS' AND policy=NEW.policy) THEN RAISE(ABORT,'correction approval mismatch') END;
END;
CREATE TRIGGER release_policy BEFORE INSERT ON release_assignments BEGIN
 SELECT CASE WHEN (SELECT policy FROM releases WHERE id=NEW.release)!=(SELECT policy FROM effective_assignments WHERE id=NEW.assignment) THEN RAISE(ABORT,'release policy mismatch') END;
END;

CREATE TRIGGER synthetic_snapshot BEFORE INSERT ON snapshots BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM sources WHERE id=NEW.source AND license_state='synthetic') THEN RAISE(ABORT,'synthetic sources only in checkpoint A') END;
END;
