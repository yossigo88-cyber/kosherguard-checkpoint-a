from pathlib import Path
import sys,json,hashlib,sqlite3
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from classifier import Store,Classifier,DESC
p=ROOT/'artifacts/synthetic.sqlite'
if p.exists():p.unlink()
s=Store(p)
s.approve('synthetic-parent','example.com','adult',DESC)
s.approve('synthetic-gambling','safe.example.com','gambling')
s.suppress('synthetic-safe','safe.example.com','adult',DESC)
s.assertion('synthetic-new-evidence','child.safe.example.com','adult')
s.release('synthetic-release-1');s.db.commit()
settings={r[0]:False for r in s.db.execute('SELECT id FROM categories')};settings['adult']=True;settings['gambling']=True
c=Classifier(s)
results=[c.classify(h,'synthetic-release-1',settings,'synthetic-settings-1') for h in ['example.com','safe.example.com','child.safe.example.com','othersafe.example.com','notexample.com']]
(ROOT/'artifacts/demo-results.json').write_text(json.dumps(results,indent=2)+'\n')
integrity={'sqlite_integrity':s.db.execute('PRAGMA integrity_check').fetchone()[0],'foreign_key_errors':[list(r) for r in s.db.execute('PRAGMA foreign_key_check')],'policy_categories':s.db.execute('SELECT count(*) FROM policy_categories').fetchone()[0],'assignments':s.db.execute('SELECT count(*) FROM effective_assignments').fetchone()[0],'corrections':s.db.execute('SELECT count(*) FROM corrections').fetchone()[0],'real_sources':0,'enforcement':False}
s.close()
(ROOT/'artifacts/integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
print(json.dumps(integrity,indent=2))
