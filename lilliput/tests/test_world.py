import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from world import open_db, snapshot, get_person, run_step, local_time, CAST, BUILDINGS
import json
from datetime import datetime
from zoneinfo import ZoneInfo

class WorldTests(unittest.TestCase):
    def test_seed_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'world.sqlite')
            db=open_db(path)
            world=snapshot(db)
            self.assertEqual(world['count'],25)
            self.assertEqual(len(world['people']),25)
            self.assertEqual(len({p['id'] for p in world['people']}),25)
            self.assertEqual(len(BUILDINGS),16)
            p=get_person(db,'tamsin-vale')
            self.assertEqual(p['job'],'Mayor')
            self.assertEqual(len(p['traits']),2)
            self.assertIsNotNone(p['journal'])
            db.close()
            second=open_db(path)
            self.assertEqual(snapshot(second)['count'],25)
            second.close()
    def test_real_calendar_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=open_db(str(Path(tmp)/'world.sqlite'))
            citizens=[json.loads(r['data']) for r in db.execute('SELECT data FROM citizens ORDER BY id')]
            w=json.loads(db.execute("SELECT value FROM meta WHERE key='world'").fetchone()['value'])
            events=[]
            # A Monday 10am in local Eastern time: mayor should be working in town hall.
            dt=datetime(2026,11,9,10,0,tzinfo=ZoneInfo('America/New_York'))
            run_step(citizens,w,int(dt.timestamp()),events)
            mayor=next(c for c in citizens if c['id']=='tamsin-vale')
            self.assertEqual(mayor['location'],'townhall')
            self.assertEqual(mayor['action'],'Reviewing town matters')
            # At midnight, mayor should sleep at home.
            dt=datetime(2026,11,10,0,0,tzinfo=ZoneInfo('America/New_York'))
            run_step(citizens,w,int(dt.timestamp()),events)
            self.assertEqual(mayor['action'],'Sleeping')
            db.close()
if __name__=='__main__':unittest.main()
