"""Synthetic-only classifier prototype. No network, app or device adapters."""
from pathlib import Path
from collections import OrderedDict
import hashlib, ipaddress, json, re, sqlite3, unicodedata
import idna

ROOT = Path(__file__).resolve().parents[1]
EXACT='EXACT_HOST'
DESC='HOST_AND_DESCENDANTS'

class ReviewRequired(ValueError): pass

class SyntheticPSL:
    version='synthetic-psl-1'
    # Reserved test namespaces only. These are fixtures, NOT the real PSL.
    rules={'test','example','invalid','localhost','com','net','org','uk','co.uk','shared.test','*.wild.test','!city.wild.test'}
    def suffix(self, host):
        labels=host.split('.')
        exceptions=[r[1:] for r in self.rules if r.startswith('!') and (host==r[1:] or host.endswith('.'+r[1:]))]
        if exceptions:
            return '.'.join(max(exceptions,key=lambda s:len(s.split('.'))).split('.')[1:])
        matches=[labels[-1]]
        for i in range(len(labels)):
            tail='.'.join(labels[i:])
            if tail in self.rules: matches.append(tail)
            if i+1<len(labels) and '*.'+'.'.join(labels[i+1:]) in self.rules: matches.append(tail)
        return max(matches,key=lambda s:len(s.split('.')))
    def validate(self, host):
        if self.suffix(host)==host: raise ValueError('public/private suffix-wide rule rejected')


def normalize(value):
    if not isinstance(value,str) or not value or value!=value.strip(): raise ValueError('invalid host')
    if any(c in value for c in '/:@?#*\\%') or any(c.isspace() for c in value): raise ValueError('host only, no wildcard/URL/port/encoding')
    if value.endswith('.'): value=value[:-1]
    if not value or value.endswith('.'): raise ValueError('ambiguous trailing dots')
    try:
        ipaddress.ip_address(value)
    except ValueError: pass
    else: raise ValueError('IP literals require a separate, unsupported policy')
    value=unicodedata.normalize('NFC',value.lower())
    try: result=idna.encode(value,uts46=False,std3_rules=True).decode('ascii')
    except idna.IDNAError as e: raise ValueError('invalid IDNA') from e
    if len(result)>253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',x) for x in result.split('.')): raise ValueError('invalid DNS labels')
    if all(x.isdigit() for x in result.split('.')): raise ValueError('ambiguous numeric host')
    return result


def matches(target, host, scope):
    return target==host or (scope==DESC and target.endswith('.'+host))


def forbidden(*args,**kwargs):
    raise AssertionError('FORBIDDEN: phone/profile/network adapter called')

enqueue=save_profile=dispatch_profile=forbidden

class Store:
    def __init__(self,path=':memory:', existing=False):
        if str(path) != ':memory:':
            resolved=Path(path).resolve()
            if ROOT/'artifacts' not in resolved.parents: raise ValueError('database must remain inside isolated artifacts directory')
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.psl=SyntheticPSL()
        if existing:
            if not self.db.execute("SELECT 1 FROM policy_versions WHERE version='1.0'").fetchone(): raise ValueError('not a prototype database')
            return
        self.db.executescript((ROOT/'src/schema.sql').read_text())
        # Evidence, policy, approvals and release manifests are immutable.
        for t in ['policy_versions','categories','policy_categories','sources','license_evidence','snapshots','hostname_rules','url_rules','source_assertions','review_decisions','effective_assignments','corrections','releases','release_assignments']:
            for op in ['UPDATE','DELETE']:
                self.db.execute(f'CREATE TRIGGER immutable_{t}_{op} BEFORE {op} ON {t} BEGIN SELECT RAISE(ABORT,"immutable record"); END;')
        self.psl=SyntheticPSL()
        data=json.loads((ROOT/'fixtures/policy-v1.0.json').read_text())
        self.policy_hash=hashlib.sha256((ROOT/'fixtures/policy-v1.0.json').read_bytes()).hexdigest()
        self.db.execute('INSERT INTO policy_versions VALUES (?,?)',('1.0',self.policy_hash))
        for c in data['categories']:
            self.db.execute('INSERT INTO categories VALUES (?,?,?)',(c['id'],c['n'],c['name']))
            self.db.execute('INSERT INTO policy_categories VALUES (?,?,?,?,?,?)',('1.0',c['id'],c['definition'],c['yes'],c['no'],c['rules']))
        self.db.execute('INSERT INTO sources VALUES (?,?,?)',('synthetic','synthetic','handwritten fixtures only'))
        self.db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?)',('fixture-1','synthetic','synthetic-content','parser-1',1))
        self.db.commit()
    def rule(self,host,scope=EXACT):
        if scope not in (EXACT,DESC): raise ValueError('explicit scope required')
        host=normalize(host);self.psl.validate(host)
        self.db.execute('INSERT OR IGNORE INTO hostname_rules(host,scope,psl_version) VALUES (?,?,?)',(host,scope,self.psl.version))
        return self.db.execute('SELECT id FROM hostname_rules WHERE host=? AND scope=?',(host,scope)).fetchone()[0]
    def decision(self,id,kind,policy='1.0',supersedes=None):
        if kind in ('REVOKE','REPLACE') and not supersedes: raise ValueError('revocation/replacement must name previous decision')
        if supersedes:
            if kind not in ('REVOKE','REPLACE'): raise ValueError('explicit revocation/replacement required')
            if self.db.execute('SELECT 1 FROM review_decisions WHERE supersedes=?',(supersedes,)).fetchone(): raise ReviewRequired('competing approval requires review')
        self.db.execute('INSERT INTO review_decisions VALUES (?,?,?,?,?,?,?)',(id,kind,policy,'synthetic-reviewer','synthetic evidence','2026-11-23T21:45:00-05:00',supersedes))
    def assertion(self,id,host,category,scope=EXACT,snapshot='fixture-1'):
        rule=self.rule(host,scope)
        self.db.execute('INSERT INTO source_assertions VALUES (?,?,?,?,?)',(id,snapshot,rule,category,'synthetic evidence'))
        self.db.execute('INSERT INTO review_queue(assertion,reason) VALUES (?,?)',(id,'classification evidence requires review'))
        return rule
    def approve(self,id,host,category,scope=EXACT):
        rule=self.assertion(id,host,category,scope);self.decision('approve-'+id,'APPROVE')
        self.db.execute('INSERT INTO effective_assignments VALUES (?,?,?,?,?,?)',(id,rule,category,id,'approve-'+id,'1.0'))
    def suppress(self,id,host,category,scope=EXACT):
        rule=self.rule(host,scope);self.decision('suppress-'+id,'SUPPRESS')
        self.db.execute('INSERT INTO corrections VALUES (?,?,?,?,?)',(id,rule,category,'suppress-'+id,'1.0'))
    def correction_version(self):
        return self.db.execute('SELECT count(*) FROM review_decisions').fetchone()[0]
    def release(self,id, assignment_ids=None):
        # Transactional membership: callers commit once complete, never partial.
        self.db.execute('INSERT INTO releases VALUES (?,?,?,?,?,?)',(id,'1.0',self.correction_version(),self.psl.version,'parser-1',hashlib.sha256(json.dumps({'release':id,'policy':'1.0','corrections':self.correction_version(),'psl':self.psl.version,'assignments':sorted(assignment_ids) if assignment_ids is not None else [r[0] for r in self.db.execute('SELECT id FROM effective_assignments ORDER BY id')]},sort_keys=True).encode()).hexdigest()))
        if assignment_ids is None:
            self.db.execute('INSERT INTO release_assignments SELECT ?,id FROM effective_assignments',(id,))
        else:
            self.db.executemany('INSERT INTO release_assignments VALUES (?,?)',[(id,a) for a in assignment_ids])
    def revoke(self,correction_id,id):
        row=self.db.execute('SELECT decision FROM corrections WHERE id=?',(correction_id,)).fetchone()
        if not row: raise ValueError('unknown correction')
        self.decision(id,'REVOKE',supersedes=row[0])
    def close(self): self.db.close()

class Classifier:
    def __init__(self,store,cache_size=32):
        if not isinstance(cache_size,int) or cache_size<0 or cache_size>4096: raise ValueError('bounded cache required')
        self.store=store;self.cache=OrderedDict();self.cache_size=cache_size
    def classify(self,target,release,settings,selection_version):
        host=normalize(target); db=self.store.db
        ids={r[0] for r in db.execute('SELECT id FROM categories')}
        if set(settings)!=ids or any(type(x) is not bool for x in settings.values()): raise ReviewRequired('complete explicit synthetic selections required; never default legacy values')
        rel=db.execute('SELECT * FROM releases WHERE id=?',(release,)).fetchone()
        if not rel: raise ValueError('unknown release')
        if rel['policy']!='1.0' or rel['psl_version']!=self.store.psl.version: raise ReviewRequired('policy/PSL mismatch')
        key=(host,release,rel['policy'],self.store.correction_version(),selection_version,tuple(sorted(settings.items())))
        if key in self.cache:
            self.cache.move_to_end(key);return json.loads(self.cache[key])
        labels=host.split('.');ancestors=['.'.join(labels[i:]) for i in range(len(labels))]
        marks=','.join('?' for _ in ancestors)
        assignments=db.execute(f'SELECT a.*,h.host,h.scope FROM release_assignments r JOIN effective_assignments a ON a.id=r.assignment JOIN hostname_rules h ON h.id=a.rule WHERE r.release=? AND h.host IN ({marks})',[release,*ancestors]).fetchall()
        corrections=db.execute(f'SELECT c.*,h.host,h.scope FROM corrections c JOIN hostname_rules h ON h.id=c.rule WHERE h.host IN ({marks}) AND NOT EXISTS(SELECT 1 FROM review_decisions d WHERE d.supersedes=c.decision)',ancestors).fetchall()
        cats=set();explanations=[];suppressed=[]
        for a in assignments:
            if not matches(host,a['host'],a['scope']):continue
            cs=[c for c in corrections if c['category']==a['category'] and matches(host,c['host'],c['scope'])]
            if any(c['policy']!=rel['policy'] for c in cs):raise ReviewRequired('correction policy review required')
            if any(len(c['host'].split('.'))<len(a['host'].split('.')) for c in cs): raise ReviewRequired('more-specific assignment competes with correction')
            if cs:
                suppressed.append({'assignment':a['id'],'corrections':sorted(c['id'] for c in cs)});continue
            cats.add(a['category']);explanations.append({'assignment':a['id'],'category':a['category'],'rule':a['host'],'scope':a['scope'],'policy_version':a['policy'],'approval':a['decision']})
        result={'status':'CLASSIFIED' if cats else ('SUPPRESSED' if suppressed else 'UNKNOWN'),'host':host,'categories':sorted(cats),'blocking_categories':sorted(c for c in cats if settings[c]),'would_block':any(settings[c] for c in cats),'policy_version':rel['policy'],'release':release,'correction_version':self.store.correction_version(),'evidence':explanations,'suppressed':suppressed,'enforcement':False}
        if self.cache_size:
            self.cache[key]=json.dumps(result,sort_keys=True)
            while len(self.cache)>self.cache_size:self.cache.popitem(last=False)
        return result
