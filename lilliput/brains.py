"""Optional Ollama-assisted decisions. Core simulation needs no LLM at all."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from world import LEISURE, get_person, local_time, apply_ai_thought


def ask_local_model(c):
    model=os.getenv('OLLAMA_MODEL','').strip()
    if not model: return None
    base=os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
    options=', '.join(LEISURE)
    friends=', '.join(list(c.get('relationships',{}))[:5])
    memories=' | '.join(m['text'] for m in c['journal'][:3])
    prompt=(
      'You are one resident of a cozy, realistic 25-person town called Lilliput. '
      'Choose ONE personally meaningful evening activity, guided by the resident\'s goals and needs. '
      'Allowed choices: '+options+'. '
      'Reply with a JSON object with exactly two keys: '
      '"choice" (one of the allowed choices) and "thought" (one vivid, first-person sentence, max 130 characters). '
      'Never introduce supernatural events, violence or new people.\n'
      f"Resident: {c['name']}, age {c['age']}, {c['job']}. "
      f"Personality: {c['temperament']}, traits: {', '.join(c['traits'])}. "
      f"Goal: {c['goal']}. Likes: {c['hobby']}. Friends: {friends}. "
      f"Current energy {c['energy']}/100, appetite {c['hunger']}/100 (lower means hungrier), "
      f"social {c['social']}/100, morale {c['mood']}/100. "
      f"Recent diary: {memories}."
    )
    payload={'model':model,'prompt':prompt,'stream':False,'format':'json',
             'options':{'temperature':0.7,'num_predict':110}}
    request=urllib.request.Request(base+'/api/generate',data=json.dumps(payload).encode(),
                                   headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=25) as response:
        outer=json.loads(response.read(1024*128))
    content=outer.get('response','')
    try:
        obj=json.loads(content)
    except Exception:
        match=re.search(r'\{.*\}',content,re.S)
        if not match: return None
        obj=json.loads(match.group(0))
    choice=str(obj.get('choice','')).lower().strip()
    thought=str(obj.get('thought','')).strip().replace('\n',' ')
    if choice not in LEISURE or not thought: return None
    return choice,thought[:230]


def maybe_ai_decide(conn,lock):
    if not os.getenv('OLLAMA_MODEL','').strip(): return False
    now=int(time.time())
    hour=local_time(now).hour
    if not (17 <= hour <= 21): return False
    date=local_time(now).strftime('%Y-%m-%d')
    with lock:
        people=[json.loads(row['data']) for row in conn.execute('SELECT data FROM citizens ORDER BY id')]
    pending=[c for c in people if c.get('last_ai_date')!=date]
    if not pending: return False
    # Balance opportunities across the whole town, not just the earliest alphabetic name.
    pending.sort(key=lambda p:(p.get('last_ai_date') or '',p['name']))
    c=pending[0]
    answer=ask_local_model(c)
    if answer:
        with lock:
            return apply_ai_thought(conn,c['id'],answer[0],answer[1],int(time.time()))
    return False
