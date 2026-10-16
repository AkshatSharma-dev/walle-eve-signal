"""WALL-E and EVE's Signal: interactive autonomous-agent simulation.
Run: python main.py
Requires Python 3.9+; no external packages.
"""
import json, math
from collections import deque
from pathlib import Path

DIRS = {'N':(0,-1),'NE':(1,-1),'E':(1,0),'SE':(1,1),'S':(0,1),'SW':(-1,1),'W':(-1,0),'NW':(-1,-1)}

def integer(prompt, minimum=0, default=None):
    while True:
        raw=input(f'{prompt}' + (f' [{default}]' if default is not None else '') + ': ').strip()
        if not raw and default is not None: return default
        try:
            n=int(raw)
            if n < minimum: print(f'Enter a value >= {minimum}.'); continue
            return n
        except ValueError: print('Enter a whole number.')

def number(prompt, minimum=0.0, maximum=1.0, default=None):
    while True:
        raw=input(f'{prompt}' + (f' [{default}]' if default is not None else '') + ': ').strip()
        if not raw and default is not None: return default
        try:
            n=float(raw)
            if n < minimum or n > maximum: print(f'Enter a value from {minimum} to {maximum}.'); continue
            return n
        except ValueError: print('Enter a number.')

def position(prompt, w, h, forbidden=None):
    forbidden=forbidden or set()
    while True:
        raw=input(f'{prompt} (x,y; x=0..{w-1}, y=0..{h-1}): ').strip()
        try:
            p=tuple(int(v.strip()) for v in raw.split(','))
            if len(p)!=2: raise ValueError
            if not (0<=p[0]<w and 0<=p[1]<h): print('Coordinate outside map.'); continue
            if p in forbidden: print('That cell is already occupied; choose another.'); continue
            return p
        except ValueError: print('Use x,y, for example 2,3.')

def yesno(prompt, default='y'):
    while True:
        v=input(f'{prompt} (y/n) [{default}]: ').strip().lower() or default
        if v in ('y','yes'): return True
        if v in ('n','no'): return False
        print('Enter y or n.')

def get_config():
    print('\n'+'='*62+'\n WALL-E AND EVE\'S SIGNAL — MISSION CONFIGURATION\n'+'='*62)
    print('Coordinates are x,y. Top-left cell is 0,0. The agent cannot see hidden clues/EVE directly.')
    w=integer('Map width',2,6); h=integer('Map height',2,5)
    print('\n-- Starting positions --')
    start=position('WALL-E start',w,h); charger=position('Charging station',w,h)
    eve=position('EVE hidden position',w,h,{start})
    print('\n-- Obstacles --')
    obstacles=set(); count=integer('Number of obstacles',0,0)
    for i in range(count):
        p=position(f'Obstacle {i+1}',w,h,obstacles|{start,charger,eve}); obstacles.add(p)
    print('\n-- Initial signal --')
    while True:
        direction=input('Signal direction (N,NE,E,SE,S,SW,W,NW): ').strip().upper()
        if direction in DIRS: break
        print('Choose one of N, NE, E, SE, S, SW, W, NW.')
    strength=number('Signal strength (0 to 1)',0,1,0.8)
    timestamp=input('Signal timestamp/label [mission-start]: ').strip() or 'mission-start'
    print('\n-- Resources and action costs --')
    battery=integer('Starting/max battery units',3,30)
    time=integer('Mission time budget (actions)',3,45)
    move_cost=integer('Battery cost per move',1,1)
    scan_cost=integer('Battery cost per scan',1,2)
    recharge_time=integer('Time cost for recharge',1,3)
    print('\n-- Hidden clue placement --')
    clues=[]; nclues=integer('Number of clues',0,2)
    for i in range(nclues):
        print(f'Clue {i+1}:')
        p=position('Clue location',w,h,obstacles)
        name=input(f'Clue name [Clue {i+1}]: ').strip() or f'Clue {i+1}'
        hint=input('Hint text [EVE may be nearby]: ').strip() or 'EVE may be nearby'
        print('Give the rectangle this clue points toward.')
        minx=integer(f'Minimum x (0..{w-1})',0,max(0,eve[0]-1)); miny=integer(f'Minimum y (0..{h-1})',0,max(0,eve[1]-1))
        maxx=integer(f'Maximum x ({minx}..{w-1})',minx,w-1); maxy=integer(f'Maximum y ({miny}..{h-1})',miny,h-1)
        clues.append({'position':p,'name':name,'hint':hint,'region':(minx,miny,maxx,maxy)})
    return {'width':w,'height':h,'start':start,'charger':charger,'eve':eve,'obstacles':obstacles,
            'signal':{'direction':direction,'strength':strength,'timestamp':timestamp},
            'battery_max':battery,'time':time,'move_cost':move_cost,'scan_cost':scan_cost,
            'recharge_time':recharge_time,'clues':clues}

class Environment:
    """Simulator stores the hidden ground truth and only returns observations."""
    def __init__(self,c):
        self.c=c; self.pos=c['start']; self.battery=c['battery_max']; self.time=c['time']
        self.finished=False; self.found=False; self.visited={self.pos}; self.scanned=set(); self.found_clues=[]
        self._eve=c['eve']; self._clues={x['position']:x for x in c['clues']}
    def observe(self):
        clue=self._clues.get(self.pos) if self.pos in self.scanned else None
        already={x['position'] for x in self.found_clues}
        if self.pos in already: clue=None
        return {'position':self.pos,'battery':self.battery,'battery_max':self.c['battery_max'],'time':self.time,
                'at_charger':self.pos==self.c['charger'],'eve_found':self.found,
                'clue':None if clue is None else {'name':clue['name'],'hint':clue['hint'],'region':clue['region']}}
    def step(self,a):
        if self.finished: return 'Mission already finished.'
        kind=a['type']; msg=''
        if kind=='move':
            dx,dy=DIRS[a['direction']]; q=(self.pos[0]+dx,self.pos[1]+dy)
            if self.battery<self.c['move_cost'] or self.time<1: msg='Move rejected: insufficient resources.'
            elif not(0<=q[0]<self.c['width'] and 0<=q[1]<self.c['height']): msg='Map boundary reached.'
            elif q in self.c['obstacles']:
                self.battery-=self.c['move_cost']; self.time-=1; msg=f'Obstacle encountered at {q}.'
            else:
                old=self.pos; self.pos=q; self.visited.add(q); self.battery-=self.c['move_cost']; self.time-=1; msg=f'Moved from {old} to {q}.'
        elif kind=='scan':
            if self.battery<self.c['scan_cost'] or self.time<1: msg='Scan rejected: insufficient resources.'
            else:
                self.battery-=self.c['scan_cost']; self.time-=1; self.scanned.add(self.pos)
                if self.pos==self._eve: self.found=True; self.finished=True; msg='EVE FOUND! Mission successful.'
                elif self.pos in self._clues:
                    cl=self._clues[self.pos]
                    if not any(x['position']==self.pos for x in self.found_clues): self.found_clues.append({'position':self.pos,'name':cl['name'],'hint':cl['hint'],'region':cl['region']})
                    msg=f'Clue found: {cl["name"]}. Hint: {cl["hint"]}'
                else: msg='Scan complete; no clue detected.'
        elif kind=='recharge':
            if self.pos!=self.c['charger']: msg='Recharge failed: not at charger.'
            elif self.time<self.c['recharge_time']: msg='Recharge failed: insufficient time.'
            else: self.battery=self.c['battery_max']; self.time-=self.c['recharge_time']; msg='Battery fully recharged.'
        elif kind=='return':
            if self.pos==self.c['charger']: self.finished=True; msg='Returned safely to the charger.'
            else: msg='Return requested but WALL-E is not at the charger.'
        else: self.finished=True; msg='Agent stopped.'
        if self.battery<=0 or self.time<=0:
            self.finished=True
            if not self.found: msg+=' Resources exhausted; mission ended.'
        return msg

class Agent:
    """Chooses actions from observations, signal bias, clue evidence, and resources."""
    def __init__(self,c):
        self.c=c; self.pos=c['start']; self.visited=set(); self.scanned=set(); self.trace=[]; self.belief={}
        dx,dy=DIRS[c['signal']['direction']]; sx,sy=c['start']; strength=c['signal']['strength']
        for y in range(c['height']):
            for x in range(c['width']):
                if (x,y)==self.pos or (x,y) in c['obstacles']: continue
                forward=(x-sx)*dx+(y-sy)*dy; side=abs((x-sx)*dy-(y-sy)*dx)
                self.belief[(x,y)]=max(.05,1+max(0,forward)*strength-side*.15)
    def update(self,o):
        self.pos=o['position']; self.visited.add(self.pos)
        clue=o['clue']
        if clue:
            minx,miny,maxx,maxy=clue['region']
            for p in self.belief:
                self.belief[p]*=4 if minx<=p[0]<=maxx and miny<=p[1]<=maxy else .2
    def bfs_step(self,start,goal,blocked):
        queue=deque([(start,[])]); seen={start}
        while queue:
            p,path=queue.popleft()
            if p==goal: return path[0] if path else None
            for d,(dx,dy) in DIRS.items():
                q=(p[0]+dx,p[1]+dy)
                if not(0<=q[0]<self.c['width'] and 0<=q[1]<self.c['height']) or q in blocked or q in seen: continue
                seen.add(q); queue.append((q,path+[d]))
        return None
    def choose(self,o,known_obstacles):
        self.update(o); p=self.pos; b=o['battery']; t=o['time']
        if o['eve_found']: return {'type':'stop'},'EVE has been found.'
        if p==self.c['charger'] and b<o['battery_max']*.65 and t>=self.c['recharge_time']+1:
            return {'type':'recharge'},'Battery is below 65%; recharge at the station.'
        if b<=self.c['move_cost']+self.c['scan_cost'] or t<=2:
            if p==self.c['charger']: return {'type':'return'},'Resources are low; finish safely at base.'
            d=self.bfs_step(p,self.c['charger'],known_obstacles)
            if d and b>=self.c['move_cost'] and t>0: return {'type':'move','direction':d},'Resources are low; head toward the charger.'
            return {'type':'stop'},'No safe return action is available.'
        if p not in self.scanned:
            self.scanned.add(p); return {'type':'scan'},'Scan this cell for EVE or a clue.'
        candidates=[(score/(1+math.dist(p,q)*.25),q) for q,score in self.belief.items() if q not in self.visited and q not in known_obstacles]
        if candidates:
            _,target=max(candidates,key=lambda x:x[0]); d=self.bfs_step(p,target,known_obstacles)
            if d: return {'type':'move','direction':d},f'Move toward promising unexplored cell {target}.'
        if p!=self.c['charger']:
            d=self.bfs_step(p,self.c['charger'],known_obstacles)
            if d: return {'type':'move','direction':d},'No unexplored cell remains; return to base.'
        return {'type':'stop'},'No further safe action is available.'

def draw_map(c,e):
    clue_positions={x['position'] for x in e.found_clues}
    print('Map: W=WALL-E, E=EVE found, #=obstacle, C=charger, ?=found clue, ·=visited, .=unknown')
    for y in range(c['height']):
        row=[]
        for x in range(c['width']):
            p=(x,y)
            if p==e.pos: ch='E' if e.found else 'W'
            elif p in c['obstacles']: ch='#'
            elif p==c['charger']: ch='C'
            elif p in clue_positions: ch='?'
            elif p in e.visited: ch='·'
            else: ch='.'
            row.append(ch)
        print(' '.join(row))

def main():
    c=get_config()
    print('\n-- Mission summary --')
    print(f'Map: {c["width"]}x{c["height"]} | Start: {c["start"]} | Charger: {c["charger"]}')
    print(f'Signal: {c["signal"]} | Battery: {c["battery_max"]} | Time: {c["time"]}')
    print(f'Obstacles: {len(c["obstacles"])} | Clues: {len(c["clues"])}')
    if not yesno('Start mission?', 'y'): print('Cancelled.'); return
    e=Environment(c); a=Agent(c); o=e.observe(); known_obstacles=set()
    while not e.finished and len(a.trace)<c['time']+10:
        action,reason=a.choose(o,known_obstacles)
        result=e.step(action); o=e.observe()
        if action['type']=='move' and 'Obstacle encountered' in result:
            dx,dy=DIRS[action['direction']]; known_obstacles.add((a.pos[0]+dx,a.pos[1]+dy))
        a.trace.append({'step':len(a.trace)+1,'position':list(a.pos),'action':action,'reason':reason,'result':result,'battery':o['battery'],'time_left':o['time']})
        print(f'\nStep {len(a.trace)} | Position {o["position"]} | Action {action}')
        print('Reason:',reason); print('Result:',result); print(f'Battery: {o["battery"]} | Time left: {o["time"]}')
        draw_map(c,e)
    report={'mission_success':e.found,'eve_location':list(e.pos) if e.found else None,
            'clues_found':[{'position':list(x['position']),'name':x['name'],'hint':x['hint'],'target_region':list(x['region'])} for x in e.found_clues],
            'visited_cells':[list(p) for p in sorted(e.visited)],'final_position':list(e.pos),
            'battery_remaining':e.battery,'time_remaining':e.time,
            'confidence':1.0 if e.found else min(.9,.2+.15*len(e.found_clues)),
            'recommended_next_step':'Report EVE location; mission complete.' if e.found else 'Increase time/battery or improve search strategy.',
            'signal':c['signal'],'trace':a.trace}
    Path('mission_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    saved={'map':{'width':c['width'],'height':c['height']},'start':list(c['start']),'charger':list(c['charger']),'eve_hidden':list(c['eve']),
           'obstacles':[list(p) for p in c['obstacles']],'signal':c['signal'],'resources':{'battery':c['battery_max'],'time':c['time']},
           'costs':{'move':c['move_cost'],'scan':c['scan_cost'],'recharge_time':c['recharge_time']},
           'clues':[{'position':list(x['position']),'name':x['name'],'hint':x['hint'],'target_region':list(x['region'])} for x in c['clues']]}
    Path('mission_config_used.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('\n'+'='*62+'\n FINAL MISSION REPORT\n'+'='*62)
    print(json.dumps({k:v for k,v in report.items() if k!='trace'},indent=2))
    print('\nSaved: mission_report.json (includes action trace)')
    print('Saved: mission_config_used.json (mission inputs)')
    print('Note: the agent only discovers clue locations by scanning them.')

if __name__=='__main__': main()
