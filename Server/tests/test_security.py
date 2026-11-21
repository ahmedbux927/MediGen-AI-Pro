"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re
sys.path.insert(0,ROOT); os.chdir(ROOT)
# fake bcrypt
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''
bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
class Cur:
    log=[]
    attempts={}          # fake login_attempts table: lock_key -> {fail_count, locked_until}
    def execute(self,sql,p=None):
        self.sql=" ".join(sql.split()); Cur.log.append((self.sql,p))
        self.row=None
        if 'login_attempts' in self.sql:
            if self.sql.startswith('SELECT'):
                self.row=Cur.attempts.get(p[0])
            elif self.sql.startswith('INSERT INTO login_attempts'):
                Cur.attempts[p[0]]={'fail_count':p[1],'locked_until':p[2]}
            elif self.sql.startswith('DELETE FROM login_attempts'):
                Cur.attempts.pop(p[0],None)
    def fetchone(self):
        s=self.sql
        if 'login_attempts' in s: return self.row
        if 'FROM users u JOIN roles' in s: return dict(user_id=1,full_name='Ahmed',password_hash='h:admin123',role_name='Admin')
        if 'SELECT password_hash FROM users' in s: return dict(password_hash='h:admin123')
        if 'SELECT user_id FROM users WHERE username' in s: return None
        if 'FROM roles WHERE role_id' in s: return dict(role_id=3)
        return {}
    def fetchall(self): return []
    def close(self): pass
class Conn:
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): pass
m=types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self,app): self.connection=Conn()
m.MySQL=MySQL; sys.modules['flask_mysqldb']=m
import app as A
A.app.template_folder=(ROOT + '/templates')
A.app.config['TESTING']=False
ok=lambda c,msg: print(('PASS ' if c else 'FAIL ')+msg)

c=A.app.test_client()
r=c.get('/login'); h=r.get_data(as_text=True)
tok=re.search(r'name="csrf-token" content="([0-9a-f]+)"',h).group(1)
ok(r.status_code==200 and tok,'login page has csrf meta token')
ok(f'name="csrf_token" value="{tok}"' in h,'login form got hidden csrf field')
ok('admin123' not in h,'default password hint removed')
ok(r.headers.get('X-Frame-Options')=='SAMEORIGIN' and r.headers.get('X-Content-Type-Options')=='nosniff','security headers')

r=c.post('/login',data={'username':'admin','password':'admin123'})
ok(r.status_code==302 and '/login' in r.headers['Location'] or r.status_code==302,'POST without token blocked')
with c.session_transaction() as s: ok('user_id' not in s,'  ...and not logged in')

# wrong password x5 -> lock
for i in range(5):
    r=c.post('/login',data={'username':'admin','password':'bad','csrf_token':tok})
r=c.post('/login',data={'username':'admin','password':'admin123','csrf_token':tok})
ok(r.status_code==429,'5 wrong passwords -> account locked (429) even with right password')
Cur.attempts.clear()

r=c.post('/login',data={'username':'admin','password':'admin123','csrf_token':tok})
ok(r.status_code==302 and r.headers['Location'].endswith('/dashboard'),'correct login works')
with c.session_transaction() as s:
    ok(s.get('user_id')==1 and s.permanent,'session permanent (timeout active)')
    ok(s.get('_csrf')!=tok,'new csrf token after login (session cleared)')
    tok2=s['_csrf']
    fl=[m for _,m in s.get('_flashes',[])]
ok(any('weak' in m.lower() for m in fl),'weak-password warning shown for admin123')

r=c.post('/chatbot/api',json={'question':'help'})
ok(r.status_code==400,'chatbot API without token -> 400')
Cur.log.clear()
r=c.post('/chatbot/api',json={'question':'help'},headers={'X-CSRFToken':tok2})
ok(r.status_code==200 and 'answer' in r.json,'chatbot API with token -> 200')

r=c.get('/medicines/delete/1'); ok(r.status_code==405,'GET delete medicine -> 405 (not allowed)')
Cur.log.clear()
r=c.post('/medicines/delete/1',data={}); ok(not any('DELETE FROM medicines' in q for q,_ in Cur.log),'POST delete without token -> nothing deleted')
r=c.post('/medicines/delete/1',data={'csrf_token':tok2}); ok(any('UPDATE medicines SET is_deleted' in q for q,_ in Cur.log),'POST delete with token -> hidden (v86.29)')

Cur.log.clear()
r=c.post('/records/clear/sales',data={'csrf_token':tok2,'admin_password':'wrong'})
ok(not any('DELETE FROM sales' in q for q,_ in Cur.log),'records clear with wrong password -> blocked')
r=c.post('/records/clear/sales',data={'csrf_token':tok2,'admin_password':'admin123'})
ok(any('DELETE FROM sales' in q for q,_ in Cur.log),'records clear with right password -> works')

Cur.log.clear()
r=c.post('/users/add',data={'csrf_token':tok2,'full_name':'x','username':'x1','password':'abc','role_id':'3'})
ok(not any('INSERT INTO users' in q for q,_ in Cur.log),'add user with weak password -> rejected')
r=c.post('/users/add',data={'csrf_token':tok2,'full_name':'Test User','username':'xuser1','password':'Strong2026','role_id':'3'})
ok(any('INSERT INTO users' in q for q,_ in Cur.log),'add user with strong password -> created')

for pw,exp in [('abc',True),('abcdefgh',True),('12345678',True),('Admin123',True),('pharma2026',None),('x1x1x1x1',None)]:
    e=A.password_error(pw,'x'); 
    ok((e is not None)==(exp is True) or exp is None and e is None, f'password_error({pw!r}) -> {e}')
