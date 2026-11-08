#!/usr/bin/env python3
"""Launch with: python3 server.py. No pip install necessary."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import re
import signal
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent

def load_dotenv():
    p=ROOT/'.env'
    if not p.is_file(): return
    for raw in p.read_text(encoding='utf-8').splitlines():
        raw=raw.strip()
        if not raw or raw.startswith('#') or '=' not in raw: continue
        key,val=raw.split('=',1)
        key=key.strip()
        if key.isidentifier(): os.environ.setdefault(key,val.strip().strip('"').strip("'"))

load_dotenv()
from world import open_db, advance, snapshot, get_person, get_recent_events
from brains import maybe_ai_decide

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('lilliput')
DB_PATH=Path(os.getenv('WORLD_DB',str(ROOT/'data/lilliput.sqlite')))
DB_PATH.parent.mkdir(parents=True,exist_ok=True)
DB=open_db(str(DB_PATH))
LOCK=threading.RLock()
with LOCK:
    advance(DB)

class Handler(SimpleHTTPRequestHandler):
    server_version='Lilliput/0.1'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT/'static'),**kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Cache-Control','no-cache' if not self.path.startswith('/api/') else 'no-store')
        super().end_headers()

    def send_json(self,body,status=200):
        data=json.dumps(body,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p=urlparse(self.path).path
        if p.startswith('/api/'):
            try:
                with LOCK:
                    if p=='/api/world': result=snapshot(DB)
                    elif p=='/api/chronicle': result={'events':get_recent_events(DB)}
                    elif p.startswith('/api/people/'):
                        pid=unquote(p[len('/api/people/'):])
                        if not re.fullmatch(r'[a-z0-9-]{1,80}',pid):
                            return self.send_json({'error':'Invalid resident'},400)
                        result=get_person(DB,pid)
                        if result is None: return self.send_json({'error':'Resident not found'},404)
                    elif p=='/api/health': result={'ok':True,'version':'0.1.0'}
                    else: return self.send_json({'error':'Unknown API route'},404)
                return self.send_json(result)
            except Exception as exc:
                log.exception('API request failed')
                return self.send_json({'error':'Internal server error'},500)
        if p=='/': self.path='/index.html'
        return super().do_GET()

    def do_POST(self):
        self.send_json({'error':'This version is a read-only observation dashboard'},405)

    def log_message(self,format,*args):
        if not self.path.startswith('/api/world'):
            super().log_message(format,*args)


def simulation_loop(stop):
    while not stop.wait(15):
        try:
            with LOCK: advance(DB)
        except Exception: log.exception('Simulation step failed')


def ai_loop(stop):
    delay=max(120,int(os.getenv('AI_INTERVAL_SECONDS','600')))
    stop.wait(12)
    while not stop.is_set():
        try:
            maybe_ai_decide(DB,LOCK)
        except Exception:
            log.exception('Optional Ollama request failed; rules-based simulation continues')
        stop.wait(delay)


def main():
    host=os.getenv('HOST','0.0.0.0')
    port=int(os.getenv('PORT','8788'))
    stop=threading.Event()
    threads=[threading.Thread(target=simulation_loop,args=(stop,),daemon=True),
             threading.Thread(target=ai_loop,args=(stop,),daemon=True)]
    for t in threads:t.start()
    httpd=ThreadingHTTPServer((host,port),Handler)
    log.info('Lilliput running at http://%s:%s (SQLite: %s)',host,port,DB_PATH)
    log.info('Optional AI: %s',os.getenv('OLLAMA_MODEL') or 'disabled (rule-based autonomy is active)')
    try: httpd.serve_forever(poll_interval=.5)
    except KeyboardInterrupt: pass
    finally:
        stop.set()
        httpd.server_close()
        with LOCK: DB.close()

if __name__=='__main__':main()
