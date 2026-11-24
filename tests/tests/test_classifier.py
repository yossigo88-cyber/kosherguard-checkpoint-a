import sys, socket, unittest, sqlite3, tempfile, json, hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from classifier import Store,Classifier,normalize,SyntheticPSL,EXACT,DESC,ReviewRequired,enqueue,save_profile,dispatch_profile

class Tests(unittest.TestCase):
    def setUp(self):
        self.network=patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden'));self.network.start()
        self.s=Store();self.c=Classifier(self.s)
        self.settings={r[0]:False for r in self.s.db.execute('SELECT id FROM categories')}
    def tearDown(self):self.s.close();self.network.stop()
    def rel(self,id='r'):self.s.release(id)
    def q(self,host,release='r'):return self.c.classify(host,release,self.settings,'settings-1')
    def parent(self):self.s.approve('parent','example.com','adult',DESC)
    def test_01_policy_checksum_and_all_28(self):
        line=(ROOT/'docs/policy-sha256.txt').read_text().split()[0]
        self.assertEqual(line,hashlib.sha256((ROOT/'docs/approved-policy-v1.0.ts').read_bytes()).hexdigest())
        self.assertEqual(len(self.settings),28)
        for c in self.settings:self.s.approve(c,c+'.test',c)
        self.rel()
        for c in self.settings:
            self.assertEqual(self.q(c+'.test')['categories'],[c]);self.assertEqual(self.q(c+'.test')['policy_version'],'1.0')
    def test_02_policy_final_exclusions(self):
        rows=json.loads((ROOT/'fixtures/policy-v1.0.json').read_text())['categories']
        self.assertIn('legitimate plagiarism detection',rows[10]['no'])
        self.assertIn('other 10 Adult & unsafe',rows[4]['definition'])
        self.assertIn('harm-reduction',rows[2]['no'])
    def test_03_baseline_inheritance_boundary(self):
        self.parent();self.rel()
        for h in ['example.com','safe.example.com','child.safe.example.com']:self.assertEqual(self.q(h)['categories'],['adult'])
        for h in ['notexample.com','example.com.evil.test']:self.assertEqual(self.q(h)['categories'],[])
    def test_04_exact_suppression_only_host(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult');self.rel()
        self.assertEqual(self.q('safe.example.com')['categories'],[])
        for h in ['example.com','child.safe.example.com']:self.assertEqual(self.q(h)['categories'],['adult'])
    def test_05_descendant_suppression(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult',DESC);self.rel()
        for h in ['safe.example.com','child.safe.example.com']:self.assertEqual(self.q(h)['status'],'SUPPRESSED')
        for h in ['example.com','othersafe.example.com']:self.assertEqual(self.q(h)['categories'],['adult'])
    def test_06_other_category_any_enabled(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult',DESC);self.s.approve('g','safe.example.com','gambling');self.rel()
        self.settings['adult']=True
        self.assertFalse(self.q('safe.example.com')['would_block'])
        self.settings['gambling']=True
        self.assertEqual(self.q('safe.example.com')['blocking_categories'],['gambling'])
        self.settings['adult']=False
        self.assertTrue(self.q('safe.example.com')['would_block'])
    def test_07_feed_repeat_remove_reappear(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult',DESC);self.rel('r1')
        self.s.release('r2',assignment_ids=[]);self.s.db.execute("DELETE FROM review_queue")
        self.s.assertion('repeat','safe.example.com','adult');self.s.assertion('reappear','child.safe.example.com','adult');self.rel('r3')
        for r in ['r1','r2','r3']:self.assertEqual(self.q('child.safe.example.com',r)['categories'],[])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM corrections').fetchone()[0],1)
    def test_08_independent_source_cannot_resurrect(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult',DESC);self.rel()
        self.s.db.execute("INSERT INTO sources VALUES ('new','synthetic','new synthetic source')")
        self.s.db.execute("INSERT INTO snapshots VALUES ('new','new','hash','parser-1',1)")
        for i,h in enumerate(['safe.example.com','child.safe.example.com']):self.s.assertion('new'+str(i),h,'adult',snapshot='new')
        self.assertEqual(self.q('child.safe.example.com')['categories'],[])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM review_queue').fetchone()[0],3)
    def test_09_exact_outside_scope_child(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult');self.s.approve('child','child.safe.example.com','adult');self.rel()
        self.assertEqual(self.q('safe.example.com')['categories'],[]);self.assertEqual(self.q('child.safe.example.com')['categories'],['adult'])
    def test_10_revocation_cache_and_audit(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult');self.rel();before=self.q('safe.example.com')
        self.s.revoke('safe','revoke-safe');after=self.q('safe.example.com')
        self.assertEqual(before['categories'],[]);self.assertEqual(after['categories'],['adult'])
        self.assertNotEqual(before['correction_version'],after['correction_version'])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM corrections').fetchone()[0],1)
        with self.assertRaises(ReviewRequired):self.s.revoke('safe','competing-revoke')
    def test_11_unresolved_more_specific_approval(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult',DESC);self.s.approve('child','child.safe.example.com','adult');self.rel()
        with self.assertRaises(ReviewRequired):self.q('child.safe.example.com')
    def test_12_normalization(self):
        self.assertEqual(normalize('SAFE.Example.COM.'),'safe.example.com')
        self.assertEqual(normalize('BÜCHER.test'),'xn--bcher-kva.test')
        self.assertEqual(normalize('xn--bcher-kva.test'),'xn--bcher-kva.test')
    def test_13_reject_bad_hostnames(self):
        for h in ['',' example.com','example.com ','a..test','example.com..','https://example.com/path','*.example.com','a:443','a/b','a%2etest','a_test','-a.test','a-.test','127.0.0.1','[::1]','::1','123.456','a'*64+'.test','\nexample.com']:
            with self.subTest(h=h),self.assertRaises(ValueError):normalize(h)
    def test_14_public_private_suffix_guard(self):
        for h in ['com','co.uk','shared.test','test','a.wild.test']:
            with self.subTest(h=h),self.assertRaises(ValueError):self.s.rule(h,DESC)
        for h in ['tenant.shared.test','city.wild.test','a.city.wild.test']:self.s.rule(h)
    def test_15_no_default_inheritance(self):
        self.s.approve('exact','example.com','adult');self.rel()
        self.assertEqual(self.q('child.example.com')['status'],'UNKNOWN')
    def test_16_shared_tenant_isolation(self):
        self.s.approve('tenant','tenant.shared.test','cloud',DESC);self.rel()
        self.assertEqual(self.q('other.shared.test')['status'],'UNKNOWN')
        self.assertEqual(self.q('child.tenant.shared.test')['categories'],['cloud'])
    def test_17_unsupported_url_inactive(self):
        self.s.db.execute("INSERT INTO url_rules(id,url,semantics) VALUES ('u','https://report.test/story','EXACT')")
        self.rel();self.assertEqual(self.q('report.test')['status'],'UNKNOWN')
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute("INSERT INTO url_rules VALUES ('bad','https://report.test/story','EXACT',1,1)")
        with self.assertRaises(ValueError):self.s.assertion('url','https://report.test/story','adult')
    def test_18_raw_evidence_not_effective(self):
        self.s.assertion('raw','example.com','adult');self.rel()
        self.assertEqual(self.q('example.com')['status'],'UNKNOWN')
    def test_19_settings_unchanged_and_cache_version(self):
        self.parent();self.rel();before=json.dumps(self.settings,sort_keys=True)
        self.q('example.com');self.assertEqual(before,json.dumps(self.settings,sort_keys=True))
        self.settings['adult']=True;self.assertTrue(self.q('example.com')['would_block'])
        bad=self.settings.copy();del bad['adult']
        with self.assertRaises(ReviewRequired):self.c.classify('example.com','r',bad,'1')
        bad=self.settings.copy();bad['adult']=1
        with self.assertRaises(ReviewRequired):self.c.classify('example.com','r',bad,'1')
    def test_20_no_phone_or_network(self):
        for f in [enqueue,save_profile,dispatch_profile]:
            with self.assertRaises(AssertionError):f('synthetic')
        with socket.socket() as sock:
            with self.assertRaises(AssertionError):sock.connect(('127.0.0.1',1))
    def test_21_immutable_records(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult');self.rel()
        for table in ['policy_versions','categories','source_assertions','review_decisions','effective_assignments','corrections','releases']:
            with self.subTest(table=table),self.assertRaises(sqlite3.IntegrityError):self.s.db.execute('DELETE FROM '+table)
    def test_22_schema_invalid_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute("INSERT INTO snapshots VALUES ('real','synthetic','h','p',0)")
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute("INSERT INTO review_decisions VALUES ('x','APPROVE',NULL,'r','e','date',NULL)")
        with self.assertRaises(sqlite3.IntegrityError):self.s.assertion('bad','example.com','bad-category')
        rule=self.s.assertion('a','example.com','adult');self.s.decision('d','SUPPRESS')
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute('INSERT INTO effective_assignments VALUES (?,?,?,?,?,?)',('bad',rule,'adult','a','d','1.0'))
    def test_23_release_rollback_transaction(self):
        self.s.db.commit();self.s.db.execute('BEGIN');self.parent();self.rel('partial');self.s.db.rollback()
        self.assertIsNone(self.s.db.execute("SELECT id FROM releases WHERE id='partial'").fetchone())
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM effective_assignments').fetchone()[0],0)
    def test_24_bounded_cache(self):
        self.rel()
        for i in range(100):self.q('host'+str(i)+'.test')
        self.assertEqual(len(self.c.cache),32)
    def test_25_psl_change_requires_review(self):
        self.parent();self.rel();self.s.psl.version='synthetic-psl-2'
        with self.assertRaises(ReviewRequired):self.q('example.com')
    def test_26_restart_and_old_feed_rollback_preserves_correction(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as d:
            p=Path(d)/'test.sqlite';s=Store(p);s.approve('a','example.com','adult',DESC);s.release('old');s.suppress('safe','safe.example.com','adult',DESC);s.release('new');s.db.commit();s.close()
            s=Store(p,existing=True);c=Classifier(s)
            for rel in ['old','new']:self.assertEqual(c.classify('child.safe.example.com',rel,self.settings,'1')['categories'],[])
            s.close()
    def test_27_replacement_audit(self):
        self.parent();self.s.suppress('old','safe.example.com','adult');self.s.revoke('old','revoke-old');self.s.suppress('new','safe.example.com','adult',DESC);self.rel()
        self.assertEqual(self.q('child.safe.example.com')['categories'],[])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM corrections').fetchone()[0],2)
    def test_28_fixture_exclusions_unknown_not_inferred(self):
        self.rel()
        for h in ['health.test','recovery.test','citation-checker.test','ordinary-writing.test','research.test','news-report.test']:self.assertEqual(self.q(h)['status'],'UNKNOWN')
    def test_29_repeated_build_deterministic(self):
        self.parent();self.rel();a=self.q('child.example.com')
        s=Store();s.approve('parent','example.com','adult',DESC);s.release('r');b=Classifier(s).classify('child.example.com','r',self.settings,'settings-1');s.close()
        self.assertEqual(a,b)
    def test_30_selection_changes_never_write_store(self):
        self.parent();self.rel();before=self.s.db.total_changes
        for c in self.settings:
            self.settings[c]=True;self.q('example.com');self.settings[c]=False
        self.assertEqual(self.s.db.total_changes,before)

    def test_31_read_only_classifier(self):
        self.parent();self.rel();self.s.db.commit()
        denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE}
        self.s.db.set_authorizer(lambda op,*args:sqlite3.SQLITE_DENY if op in denied else sqlite3.SQLITE_OK)
        self.assertEqual(self.q('child.example.com')['categories'],['adult'])
    def test_32_synthetic_only_and_path_guard(self):
        with self.assertRaises(ValueError):Store('/tmp/outside-checkpoint.sqlite')
        self.s.db.execute("INSERT INTO sources VALUES ('real','cleared','fixture label only')")
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute("INSERT INTO snapshots VALUES ('bad','real','hash','p',1)")
    def test_33_revocation_needs_target(self):
        with self.assertRaises(ValueError):self.s.decision('bad','REVOKE')
    def test_34_same_host_new_approved_assertion_suppressed(self):
        self.parent();self.s.suppress('safe','safe.example.com','adult');self.s.approve('new','safe.example.com','adult');self.rel()
        self.assertEqual(self.q('safe.example.com')['categories'],[])
    def test_35_invalid_cache_and_release(self):
        with self.assertRaises(ValueError):Classifier(self.s,cache_size=100000)
        with self.assertRaises(ValueError):self.q('example.com','missing')

if __name__=='__main__':unittest.main(verbosity=2)
