"""Lilliput's deterministic, persistent, real-time village simulation.
Standard library only; the phone is a viewer, never the simulation host.
"""
from __future__ import annotations
import json
import math
import os
import random
import sqlite3
import time
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_NAME = os.getenv('LILLIPUT_TIMEZONE', 'America/New_York')
try:
    TZ = ZoneInfo(TZ_NAME)
except Exception:
    TZ_NAME = 'UTC'
    TZ = ZoneInfo('UTC')
STEP_SECONDS = 15 * 60

BUILDINGS = [
    {'id':'townhall','name':'Town Hall','icon':'🏛️','description':'Civic decisions, messages, and village records','kind':'Civic'},
    {'id':'bakery','name':'Oven & Hearth','icon':'🥖','description':'Warm bread and early-morning conversation','kind':'Commerce'},
    {'id':'market','name':'Trading Square','icon':'🧺','description':'Groceries, parcels, and the town noticeboard','kind':'Commerce'},
    {'id':'school','name':'Schoolhouse','icon':'📚','description':'Lessons, crafts, and stories','kind':'Community'},
    {'id':'clinic','name':'Little Clinic','icon':'⚕️','description':'Care and herbal remedies','kind':'Community'},
    {'id':'workshop','name':'Tinker Workshop','icon':'🔧','description':'Repairs, woodworking, and construction','kind':'Industry'},
    {'id':'farm','name':'Greenacre Farm','icon':'🌾','description':'Vegetables, orchards, and garden plots','kind':'Outdoors'},
    {'id':'pond','name':'Silver Pond','icon':'🐟','description':'Fishing and quiet waterside walks','kind':'Outdoors'},
    {'id':'tavern','name':'The Lantern Inn','icon':'🍲','description':'Dinner, warm drinks, and neighborhood gossip','kind':'Community'},
    {'id':'library','name':'Reading Nook','icon':'📖','description':'Books, artwork, and study','kind':'Community'},
    {'id':'watch','name':'Village Watch','icon':'🔔','description':'Public safety and maintenance','kind':'Civic'},
    {'id':'park','name':'Clover Park','icon':'🌳','description':'Walks, leisure, and meetups','kind':'Outdoors'},
    {'id':'willow','name':'Willow Cottages','icon':'🏠','description':'Homes along the willow-lined path','kind':'Homes'},
    {'id':'pebble','name':'Pebble Row','icon':'🏘️','description':'Cheerful little terraced homes','kind':'Homes'},
    {'id':'moss','name':'Moss Lane','icon':'🏡','description':'Quiet homes beside a garden lane','kind':'Homes'},
    {'id':'orchard','name':'Orchard Homes','icon':'🍎','description':'Homes near the apple trees','kind':'Homes'},
]
BUILDING_BY_ID = {b['id']: b for b in BUILDINGS}

# name, age, job, workplace, shift, personality, trait1, trait2, hobby, dream, biography
CAST = [
 ('Tamsin Vale',46,'Mayor','townhall',9,'steadfast','Diplomatic','Patient','stroll','Keep the town united','A practiced listener who remembers every promise and worries over everyone.'),
 ('Rowan Pike',32,'Town clerk','townhall',9,'methodical','Meticulous','Reserved','read','Preserve the town chronicles','Keeps careful records and has a dry sense of humor.'),
 ('Juniper Reed',38,'Baker','bakery',5,'warm','Generous','Restless','create','Bake the perfect festival cake','Gets up before dawn and measures happiness in loaves shared.'),
 ('Otis Bloom',20,'Baker apprentice','bakery',6,'playful','Curious','Clumsy','socialize','Become a master baker','Always covered in flour, always eager to learn.'),
 ('Mira Solis',41,'Grocer','market',8,'outgoing','Observant','Sociable','socialize','Open a thriving bazaar','Knows everyone’s favorite snack and notices even small changes.'),
 ('Theo Wren',27,'Market helper','market',10,'gentle','Helpful','Shy','read','See the world beyond town','Keeps a pocket notebook of places he hopes to visit.'),
 ('Pippa Finch',34,'Teacher','school',8,'bright','Imaginative','Patient','read','Build a wonderful school library','Turns everything, even a walk, into a lesson.'),
 ('Elias Moss',57,'School caretaker','school',7,'quiet','Reliable','Wry','stroll','Restore the old school clock','Can repair a door hinge and tell the time by the shadows.'),
 ('Amara Bell',43,'Physician','clinic',8,'focused','Compassionate','Determined','read','Improve care for everyone','Will skip her own break before leaving a neighbor unattended.'),
 ('Silas Hart',29,'Nurse','clinic',12,'empathetic','Attentive','Optimistic','socialize','Make the clinic welcoming','Remembers names, birthdays, and who needs an encouraging word.'),
 ('Fen Alder',51,'Carpenter','workshop',7,'solid','Inventive','Stubborn','create','Build a bridge across Silver Pond','Believes every problem has a practical solution, preferably wooden.'),
 ('Edie Flint',24,'Tinkerer','workshop',9,'curious','Brilliant','Impulsive','create','Invent something that helps the whole town','Collects screws, odd springs, and ideas that rarely stay small.'),
 ('Bram Fields',49,'Farmer','farm',5,'grounded','Hardworking','Protective','stroll','Make Greenacre self-sufficient','Treats the vegetable patches like members of his family.'),
 ('Ivy Fields',45,'Farmer','farm',6,'cheerful','Practical','Kind','socialize','Grow prizewinning tomatoes','Can tell the weather by the air and loves sharing the harvest.'),
 ('Nessa Brook',22,'Gardener','farm',7,'dreamy','Gentle','Creative','create','Plant a garden for every household','Sees tiny possibilities where everyone else sees bare earth.'),
 ('Kit Marlow',36,'Fisher','pond',5,'independent','Adventurous','Pensive','stroll','Chart every corner of Silver Pond','Comes home with fish, stories, and occasionally neither.'),
 ('Cora Willow',44,'Cook','tavern',12,'fiery','Skilled','Protective','socialize','Host a feast for all 25 neighbors','Runs her kitchen with warmth, speed, and firm opinions.'),
 ('Hugo Dusk',53,'Innkeeper','tavern',15,'jovial','Sociable','Forgetful','socialize','Keep the Lantern Inn bustling','Can turn a brief greeting into an hour-long conversation.'),
 ('Maeve Quill',61,'Librarian','library',10,'scholarly','Wise','Private','read','Catalog every story in Lilliput','Collects folktales and likes people more than she admits.'),
 ('Dorian Swift',26,'Courier','townhall',8,'energetic','Quick','Friendly','stroll','Know every path by heart','Always on the move and always carrying two extra messages.'),
 ('Freya Stone',39,'Constable','watch',14,'watchful','Brave','Fair','stroll','Keep every street peaceful','A calm presence with a remarkable eye for trouble.'),
 ('Len Marsh',58,'Groundskeeper','watch',6,'stoic','Dependable','Thoughtful','create','Make the town spotless and green','Wakes early to care for places everyone else takes for granted.'),
 ('Lark Ember',31,'Artist','library',10,'expressive','Sensitive','Imaginative','create','Paint the town’s biggest mural','Sketches ordinary moments as if they were important history.'),
 ('Basil Crane',35,'Builder','workshop',7,'ambitious','Strong','Patient','create','Build a second neighborhood','Wants to leave behind structures that last longer than he does.'),
 ('Saffron Hale',47,'Herbalist','clinic',9,'reflective','Knowledgeable','Gentle','read','Grow a medicinal herb garden','Knows plants by scent and chooses words with the same care.'),
]
HOMES = ['willow','pebble','moss','orchard']
WORK_ACTIONS = {
 'Mayor':'Reviewing town matters','Town clerk':'Updating the records','Baker':'Baking fresh bread',
 'Baker apprentice':'Kneading dough','Grocer':'Helping customers','Market helper':'Restocking shelves',
 'Teacher':'Teaching lessons','School caretaker':'Tending the schoolhouse','Physician':'Seeing patients',
 'Nurse':'Caring for neighbors','Carpenter':'Making furniture','Tinkerer':'Working on an invention',
 'Farmer':'Tending the fields','Gardener':'Caring for the gardens','Fisher':'Fishing at the pond',
 'Cook':'Preparing a meal','Innkeeper':'Welcoming guests','Librarian':'Cataloging books',
 'Courier':'Delivering letters','Constable':'Patrolling the lanes','Groundskeeper':'Maintaining the paths',
 'Artist':'Creating new artwork','Builder':'Working on repairs','Herbalist':'Preparing herbal remedies',
}
LEISURE = {
 'socialize':('Visiting friends','tavern'),
 'read':('Reading quietly','library'),
 'stroll':('Taking a leisurely walk','park'),
 'create':('Working on a personal project','workshop'),
 'rest':('Resting at home',None),
}


def clamp(value, low=0, high=100):
    return round(max(low, min(high, value)), 1)


def slug(value):
    return value.lower().replace(' ', '-')


def local_time(ts):
    return datetime.fromtimestamp(ts, TZ)


def json_dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def open_db(path):
    conn = sqlite3.connect(path, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.execute('CREATE TABLE IF NOT EXISTS citizens (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, person_id TEXT, message TEXT NOT NULL, category TEXT NOT NULL)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC)')
    if not conn.execute('SELECT 1 FROM citizens LIMIT 1').fetchone():
        now = int(time.time())
        residents = []
        for i, entry in enumerate(CAST):
            (name, age, role, workplace, start, temperament, trait_a, trait_b, hobby, goal, bio) = entry
            citizen = {
                'id':slug(name),'name':name,'age':age,'job':role,'workplace':workplace,
                'shift_start':start,'shift_end':(start+8)%24,'home':HOMES[i%4],
                'temperament':temperament,'traits':[trait_a,trait_b],
                'hobby':hobby,'goal':goal,'bio':bio,
                'energy':round(65+(i*7)%31,1),'hunger':round(65+(i*11)%26,1),
                'mood':round(64+(i*13)%28,1),'social':round(55+(i*17)%40,1),
                'health':round(79+(i*5)%19,1),'money':35+(i*7)%45,
                'location':HOMES[i%4],'action':'Settling into the town',
                'thought':'I wonder what today will bring.',
                'relationships':{},'journal':[{'ts':now,'text':'A new chapter begins in Lilliput.'}],
                'ai_choice':None,'last_ai_date':None,'last_action':'',
            }
            residents.append(citizen)
        for i, c in enumerate(residents):
            # A recognizable pre-existing web of friends, separate from work/social acquaintances.
            peers = [(i+1)%25,(i+4)%25,(i+11)%25]
            c['relationships']={residents[k]['id']: 48+(i+k)%30 for k in peers}
        for c in residents:
            conn.execute('INSERT INTO citizens(id,data) VALUES (?,?)',(c['id'],json_dump(c)))
        world = {'town_name':'Lilliput','founded_ts':now,'last_step':(now//STEP_SECONDS)*STEP_SECONDS-STEP_SECONDS,
                 'food':75.0,'harmony':80.0,'prosperity':70.0,'knowledge':38.0,'day_count':1}
        conn.execute('INSERT INTO meta(key,value) VALUES (?,?)',('world',json_dump(world)))
        conn.execute('INSERT INTO events(ts,person_id,message,category) VALUES (?,?,?,?)',
                     (now,None,'Lilliput is founded. Twenty-five residents move into their new town.','milestone'))
        conn.commit()
    return conn


def note(c, ts, line):
    c['journal'].insert(0, {'ts':ts,'text':line})
    c['journal'] = c['journal'][:18]


def add_event(events, ts, line, cat='life', cid=None):
    events.append((ts,cid,line,cat))


def off_day(c, dt):
    # Essential services use staggered days off; civic and school employees work weekdays.
    if c['workplace'] in ('school','townhall'):
        return dt.weekday() >= 5
    index = next((i for i, item in enumerate(CAST) if slug(item[0]) == c['id']),0)
    return dt.weekday() in ((index+2)%7, (index+4)%7)


def free_time_choice(c, ts):
    if c.get('ai_choice') in LEISURE and c.get('last_ai_date') == local_time(ts).strftime('%Y-%m-%d') and 18 <= local_time(ts).hour < 22:
        return c['ai_choice']
    if c['energy'] < 27: return 'rest'
    if c['social'] < 35: return 'socialize'
    hour_group = ts//(60*60*2)
    rng = random.Random(f"{c['id']}-{hour_group}")
    if rng.random() < .64: return c['hobby']
    return rng.choice(['socialize','read','stroll','create','rest'])


def decide(c, dt, ts):
    hour = dt.hour + dt.minute/60
    shift_start, shift_end = c['shift_start'],c['shift_end']
    active = not off_day(c,dt)
    home = c['home']
    if 23 <= hour or hour < 5:
        return home, 'Sleeping', 'sleep'
    if active and shift_start <= hour < shift_start+8:
        # A brief lunch break halfway through a shift.
        if shift_start+3.75 <= hour < shift_start+4.25:
            return 'tavern' if c['workplace']!='tavern' else 'tavern','Having lunch','eat'
        if c['hunger'] < 18:
            return c['workplace'],'Eating a quick snack','eat'
        return c['workplace'],WORK_ACTIONS.get(c['job'],'Working'), 'work'
    if active and shift_start-.75 <= hour < shift_start:
        return home,'Getting ready for work','prepare'
    if 6.75 <= hour < 7.75 and c['hunger'] < 74:
        return home,'Eating breakfast','eat'
    if 17.5 <= hour < 19.0 and c['hunger'] < 80:
        return home,'Having supper','eat'
    if c['hunger'] < 16:
        return home,'Making something to eat','eat'
    choice = free_time_choice(c,ts)
    label, location = LEISURE[choice]
    return location or home,label,choice


def run_step(citizens, world, ts, events):
    dt = local_time(ts)
    by_id = {c['id']:c for c in citizens}
    if dt.hour == 0 and dt.minute == 0:
        world['day_count'] = max(1,(dt.date()-local_time(world['founded_ts']).date()).days+1)
        add_event(events,ts,f"A new day begins in Lilliput: {dt.strftime('%A, %B %d')}.",'town')
        world['food'] = clamp(world['food']-.20)
        world['harmony'] = clamp(world['harmony']-.10)
    for c in citizens:
        old_action = c['action']
        loc,action,kind = decide(c,dt,ts)
        c['location'],c['action'] = loc,action
        c['last_action'] = kind
        if kind == 'sleep':
            c['energy']=clamp(c['energy']+2.2)
            c['hunger']=clamp(c['hunger']-.38)
            c['social']=clamp(c['social']-.11)
        elif kind == 'eat':
            c['hunger']=clamp(c['hunger']+8.5)
            c['energy']=clamp(c['energy']+.5)
            world['food']=clamp(world['food']-.014)
        elif kind == 'work':
            c['energy']=clamp(c['energy']-.72)
            c['hunger']=clamp(c['hunger']-.68)
            c['social']=clamp(c['social']-.10)
            world['prosperity']=clamp(world['prosperity']+.0025)
            if c['workplace'] in ('farm','pond','bakery'): world['food']=clamp(world['food']+.008)
            if c['workplace'] in ('school','library'): world['knowledge']=clamp(world['knowledge']+.008)
        elif kind == 'rest':
            c['energy']=clamp(c['energy']+1.4)
            c['hunger']=clamp(c['hunger']-.45)
        else:
            c['energy']=clamp(c['energy']-.30)
            c['hunger']=clamp(c['hunger']-.48)
            if kind == 'socialize': c['social']=clamp(c['social']+.85)
            if kind in ('read','create'): c['mood']=clamp(c['mood']+.18)
        if c['hunger'] < 24 or c['energy'] < 20:
            c['mood']=clamp(c['mood']-.25)
        elif c['hunger'] > 55 and c['energy'] > 45:
            c['mood']=clamp(c['mood']+.07)
        # Save journal entries at major transitions, not every fifteen-minute tick.
        if action != old_action and (dt.minute == 0 or kind in ('sleep','eat')):
            if len(events) < 10000: note(c,ts,action+'.')
        if kind=='work' and dt.hour==c['shift_start'] and dt.minute==0:
            c['money']+=2
        if dt.hour==c['shift_start']+7 and dt.minute==45 and kind=='work':
            if c['hunger']>=20 and c['energy']>=15:
                c['mood']=clamp(c['mood']+.4)
    # Shared-location interactions at the top of each hour.
    if dt.minute == 0 and 7 <= dt.hour <= 22:
        locations={}
        for c in citizens:
            if c['last_action']!='sleep':
                locations.setdefault(c['location'],[]).append(c)
        rng = random.Random(ts)
        options=[(place,people) for place, people in locations.items() if len(people)>1 and place not in HOMES]
        rng.shuffle(options)
        for place, people in options[:2]:
            a,b=rng.sample(people,2)
            a['social']=clamp(a['social']+1.5)
            b['social']=clamp(b['social']+1.5)
            a['mood']=clamp(a['mood']+.4)
            b['mood']=clamp(b['mood']+.4)
            a['relationships'][b['id']]=min(100,a['relationships'].get(b['id'],35)+1)
            b['relationships'][a['id']]=min(100,b['relationships'].get(a['id'],35)+1)
            place_name=BUILDING_BY_ID[place]['name']
            line=f"{a['name']} and {b['name']} caught up at {place_name}."
            note(a,ts,f"Talked with {b['name']} at {place_name}.")
            note(b,ts,f"Talked with {a['name']} at {place_name}.")
            add_event(events,ts,line,'social',a['id'])
            world['harmony']=clamp(world['harmony']+.01)
    if dt.minute==0 and dt.hour in (7,12,18):
        # A sparse village-wide bulletin; useful for catching up after closing the app.
        active=sum(1 for c in citizens if c['last_action']=='work')
        if active>=3:
            add_event(events,ts,f'{active} Lilliputians are at work around town.','town')


def advance(conn, max_days=7):
    row = conn.execute("SELECT value FROM meta WHERE key='world'").fetchone()
    world=json.loads(row['value'])
    now=int(time.time())
    current=(now//STEP_SECONDS)*STEP_SECONDS
    previous=int(world['last_step'])
    if current<=previous: return
    if current-previous>max_days*86400:
        previous=current-max_days*86400
        world['last_step']=previous
    citizens=[json.loads(row['data']) for row in conn.execute('SELECT data FROM citizens ORDER BY id')]
    events=[]
    for ts in range(previous+STEP_SECONDS,current+1,STEP_SECONDS):
        run_step(citizens,world,ts,events)
    world['last_step']=current
    with conn:
        conn.executemany('UPDATE citizens SET data=? WHERE id=?',[(json_dump(c),c['id']) for c in citizens])
        conn.execute("UPDATE meta SET value=? WHERE key='world'",(json_dump(world),))
        if events:
            conn.executemany('INSERT INTO events(ts,person_id,message,category) VALUES (?,?,?,?)',events)
        # Chronicle contains the most recent 30 days / up to 6000 events.
        conn.execute('DELETE FROM events WHERE ts < ?', (now-30*86400,))
        conn.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 6000)')


def snapshot(conn):
    world=json.loads(conn.execute("SELECT value FROM meta WHERE key='world'").fetchone()['value'])
    citizens=[json.loads(row['data']) for row in conn.execute('SELECT data FROM citizens ORDER BY id')]
    # Omit larger dossier fields from the frequently refreshed overview payload.
    public=[{k:v for k,v in c.items() if k not in ('relationships','journal','bio')} for c in citizens]
    events=[dict(row) for row in conn.execute('SELECT id,ts,person_id,message,category FROM events ORDER BY ts DESC,id DESC LIMIT 45')]
    return {'world':world,'people':public,'buildings':BUILDINGS,'events':events,
            'now_ts':int(time.time()),'timezone':TZ_NAME,'count':len(citizens),
            'ai_enabled':bool(os.getenv('OLLAMA_MODEL','').strip())}


def get_person(conn,pid):
    row=conn.execute('SELECT data FROM citizens WHERE id=?',(pid,)).fetchone()
    return json.loads(row['data']) if row else None


def get_recent_events(conn,limit=200):
    return [dict(r) for r in conn.execute('SELECT id,ts,person_id,message,category FROM events ORDER BY ts DESC,id DESC LIMIT ?', (limit,))]


def apply_ai_thought(conn, pid, choice, thought, ts):
    c=get_person(conn,pid)
    if not c: return False
    day=local_time(ts).strftime('%Y-%m-%d')
    if c.get('last_ai_date')==day: return False
    c['ai_choice']=choice if choice in LEISURE else c['hobby']
    c['thought']=thought[:240]
    c['last_ai_date']=day
    note(c,ts,f"I decided to {c['ai_choice']} tonight. {c['thought']}")
    with conn:
        conn.execute('UPDATE citizens SET data=? WHERE id=?',(json_dump(c),pid))
        conn.execute('INSERT INTO events(ts,person_id,message,category) VALUES (?,?,?,?)',
                     (ts,pid,f"{c['name']} made a personal decision for the evening.",'thought'))
    return True
