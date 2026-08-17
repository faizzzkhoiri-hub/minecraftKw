import pygame, math, random, json, os, sys, time
from enum import IntEnum
pygame.init()
try: pygame.mixer.init()
except: pass

W,H=pygame.display.Info().current_w or 1280, pygame.display.Info().current_h or 720
screen=pygame.display.set_mode((W,H), pygame.FULLSCREEN|pygame.SCALED)
pygame.display.set_caption('MiniCraft Mobile')
clock=pygame.time.Clock()
font=pygame.font.Font(None, max(22,H//32)); small=pygame.font.Font(None,max(18,H//42)); big=pygame.font.Font(None,max(34,H//20))

class B(IntEnum): AIR=0; GRASS=1; DIRT=2; STONE=3; WOOD=4; LEAVES=5; SAND=6; GRAVEL=7; COBBLE=8; LOG=9; WATER=10; LAVA=11; COAL=12; IRON=13; GLASS=14; PLANK=15
COL={B.GRASS:(74,170,68),B.DIRT:(130,82,45),B.STONE:(120,120,125),B.WOOD:(125,78,38),B.LEAVES:(50,145,60),B.SAND:(220,200,145),B.GRAVEL:(145,145,140),B.COBBLE:(95,95,95),B.LOG:(110,68,35),B.WATER:(45,125,205),B.LAVA:(235,90,20),B.COAL:(45,45,45),B.IRON:(180,145,115),B.GLASS:(180,225,240),B.PLANK:(190,130,70)}
NAME={b:b.name.title() for b in B}
SOLID={b:True for b in B}; SOLID.update({B.AIR:False,B.WATER:False,B.LAVA:False})
HARD={B.GRASS:1,B.DIRT:1,B.STONE:3,B.WOOD:2,B.LEAVES:1,B.SAND:1,B.GRAVEL:1,B.COBBLE:4,B.LOG:2,B.COAL:4,B.IRON:5,B.GLASS:1,B.PLANK:2}
DROP={B.GRASS:B.DIRT,B.STONE:B.COBBLE,B.LOG:B.WOOD,B.COAL:B.COAL,B.IRON:B.IRON,B.GLASS:B.GLASS,B.PLANK:B.PLANK}
HOT=[B.DIRT,B.WOOD,B.COBBLE,B.STONE,B.SAND,B.LOG,B.PLANK,B.GLASS,B.COAL]
RECIPES=[('Planks',{B.WOOD:1},{B.PLANK:4}),('Stick',{B.PLANK:2},{'stick':4}),('Wood Pick',{B.PLANK:3,'stick':2},{'tool':'wood_pick'}),('Stone Pick',{B.COBBLE:3,'stick':2},{'tool':'stone_pick'}),('Iron Pick',{B.IRON:3,'stick':2},{'tool':'iron_pick'}),('Glass',{B.SAND:1},{B.GLASS:1})]
SAVE_DIR='saves'; os.makedirs(SAVE_DIR,exist_ok=True)

class World:
 def __init__(self,seed=None): self.seed=seed or random.randrange(1,2**31); self.blocks={}; self.mobs=[]; self.time=0; self.generated=set()
 def noise(self,x,z):
  r=random.Random((self.seed*73856093+x*19349663+z*83492791)&0xffffffff); return r.random()
 def gen_chunk(self,cx,cz):
  if (cx,cz) in self.generated:return
  self.generated.add((cx,cz)); random.seed(self.seed+cx*991+cz*313)
  for x in range(cx*12,cx*12+12):
   for z in range(cz*12,cz*12+12):
    n=(math.sin(x*.09)+math.cos(z*.08)+math.sin((x+z)*.035))*.5
    h=max(2,min(22,9+int(n*5+self.noise(x//3,z//3)*2)))
    beach=h<=6
    for y in range(h): self.blocks[(x,y,z)]=B.STONE if y<h-4 else (B.SAND if beach else B.DIRT)
    self.blocks[(x,h,z)]=B.SAND if beach else B.GRASS
    if h>7 and random.random()<.035:
     for y in range(h+1,h+5):self.blocks[(x,y,z)]=B.LOG
     for dx in range(-2,3):
      for dz in range(-2,3):
       if dx*dx+dz*dz<7:self.blocks[(x+dx,h+5,z+dz)]=B.LEAVES
    if random.random()<.06:
     oy=random.randint(2,max(2,h-4)); self.blocks[(x,oy,z)]=B.COAL if random.random()<.6 else B.IRON
    if beach and random.random()<.025:self.blocks[(x,h,z)]=B.WATER
 def ensure(self,x,z,r=1):
  cx,cz=math.floor(x/12),math.floor(z/12)
  for a in range(cx-r,cx+r+1):
   for b in range(cz-r,cz+r+1):self.gen_chunk(a,b)
 def get(self,x,y,z): return self.blocks.get((int(x),int(y),int(z)),B.AIR) if y>=0 else B.STONE
 def set(self,x,y,z,b):
  if 0<=y<128:self.blocks[(int(x),int(y),int(z))]=b
 def surface(self,x,z):
  for y in range(127,0,-1):
   if SOLID.get(self.get(x,y,z),False):return y+1
  return 10
 def save(self,p,slot='world.json'):
  data={'seed':self.seed,'time':self.time,'player':p.pack(),'blocks':[[x,y,z,b.value] for (x,y,z),b in self.blocks.items()]}
  with open(os.path.join(SAVE_DIR,slot),'w') as f:json.dump(data,f)
 def load(self,p,slot='world.json'):
  path=os.path.join(SAVE_DIR,slot)
  if not os.path.exists(path):return False
  with open(path) as f:d=json.load(f)
  self.seed=d['seed'];self.time=d.get('time',0);self.blocks={(a,b,c):B(v) for a,b,c,v in d.get('blocks',[])};self.generated=set();p.unpack(d.get('player',{}));return True

class Player:
 def __init__(self,w):
  self.x=.5;self.z=.5;self.y=w.surface(0,0);self.yaw=0;self.pitch=0;self.vy=0;self.ground=False;self.hp=20;self.food=20;self.sat=5;self.inv={B.DIRT:16,B.WOOD:4,B.COBBLE:8,B.STONE:4};self.tools={'hand':999,'wood_pick':60,'stone_pick':132,'iron_pick':251};self.tool='hand';self.sel=0;self.breaking=None;self.progress=0;self.attack_cd=0
 def pack(self):return {'x':self.x,'y':self.y,'z':self.z,'yaw':self.yaw,'pitch':self.pitch,'hp':self.hp,'food':self.food,'inv':{str(int(k)):v for k,v in self.inv.items()},'tools':self.tools,'tool':self.tool,'sel':self.sel}
 def unpack(self,d):
  for k in ('x','y','z','yaw','pitch','hp','food'):setattr(self,k,d.get(k,getattr(self,k)))
  self.inv={B(int(k)):v for k,v in d.get('inv',{}).items()};self.tools=d.get('tools',self.tools);self.tool=d.get('tool','hand');self.sel=d.get('sel',0)
 def solid_at(self,w,x,y,z):return SOLID.get(w.get(math.floor(x),math.floor(y),math.floor(z)),False)
 def move(self,w,dx,dz):
  nx=self.x+dx; nz=self.z+dz
  if not any(self.solid_at(w,nx+sx,self.y,nz+sz) for sx in (-.28,.28) for sz in (-.28,.28)):self.x=nx;self.z=nz
 def update(self,w,dt,keys):
  w.ensure(self.x,self.z,2); speed=4.2*dt
  f=(keys[pygame.K_w]-keys[pygame.K_s]);s=(keys[pygame.K_d]-keys[pygame.K_a]);ln=math.hypot(f,s) or 1
  sy,cy=math.sin(self.yaw),math.cos(self.yaw);self.move(w,(sy*f+cy*s)/ln*speed,(-cy*f+sy*s)/ln*speed)
  self.vy-=18*dt;ny=self.y+self.vy*dt
  if self.vy<0 and self.solid_at(w,self.x,ny-.9,self.z): self.y=math.floor(ny)+1;self.vy=0;self.ground=True
  else:self.y=ny;self.ground=False
  if self.y<0:self.hp=0
  self.food=max(0,self.food-dt/180);self.attack_cd=max(0,self.attack_cd-dt)

class Mob:
 def __init__(self,x,y,z,t):self.x=x;self.y=y;self.z=z;self.t=t;self.hp=20 if t in ('zombie','creeper') else 10;self.cd=0
 def update(self,w,p,dt):
  self.cd=max(0,self.cd-dt);dx=p.x-self.x;dz=p.z-self.z;d=math.hypot(dx,dz)
  if self.t=='zombie' and d<18:
   self.x+=dx/d*1.2*dt if d else 0;self.z+=dz/d*1.2*dt if d else 0
   if d<1.4 and self.cd<=0:p.hp-=2;self.cd=1
  else:
   a=math.sin(time.time()+self.x)*.7;self.x+=a*dt;self.z+=math.cos(time.time()+self.z)*dt*.5
  self.y=w.surface(self.x,self.z)

class Game:
 def __init__(self):
  self.world=World();self.p=Player(self.world);self.world.ensure(0,0,3);self.inv_open=False;self.craft_open=False;self.menu=False;self.touch={};self.last_save=0;self.cross=(W//2,H//2);self.mobs=[]
  for _ in range(10):
   x=random.randint(-20,20);z=random.randint(-20,20);self.mobs.append(Mob(x+.5,self.world.surface(x,z),z+.5,random.choice(['zombie','sheep','creeper'])))
 def project(self,x,y,z):
  dx=x-self.p.x;dy=y-self.p.y;dz=z-self.p.z; sy,cy=math.sin(self.p.yaw),math.cos(self.p.yaw);rx=cy*dx-sy*dz;rz=sy*dx+cy*dz;rz=max(.2,rz);f=min(W,H)*.9; sx=W/2+rx/rz*f;sy2=H/2-(dy* f/rz)+math.tan(self.p.pitch)*f;return sx,sy2,rz
 def cube(self,x,y,z,b):
  pts=[self.project(x+dx,y+dy,z+dz) for dx,dy,dz in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
  if min(q[2] for q in pts)>35:return
  c=COL.get(b,(200,200,200)); faces=[([0,1,2,3],1.0),([4,5,6,7],.78),([3,2,6,7],1.12),([0,1,5,4],.62)]
  for ids,shade in faces:
   poly=[(pts[i][0],pts[i][1]) for i in ids]; pygame.draw.polygon(screen,tuple(max(0,min(255,int(v*shade))) for v in c),poly);pygame.draw.polygon(screen,(30,30,30),poly,1)
 def render(self):
  sky=(38,90,145) if (self.world.time%1200)<600 else (12,18,38);screen.fill(sky);self.world.ensure(self.p.x,self.p.z,2)
  vis=[]
  for (x,y,z),b in self.world.blocks.items():
   if b==B.AIR:continue
   d=(x-self.p.x)**2+(z-self.p.z)**2
   if d<32*32:vis.append((d,(x,y,z),b))
  for _,pos,b in sorted(vis,reverse=True):self.cube(*pos,b)
  for m in self.mobs:
   sx,sy,d=self.project(m.x,m.y,m.z)
   if d<25:col=(60,180,70) if m.t=='sheep' else ((50,50,50) if m.t=='creeper' else (80,150,80));r=max(5,int(260/d));pygame.draw.rect(screen,col,(sx-r,sy-2*r,2*r,2*r))
  pygame.draw.line(screen,(245,245,245),(W//2-8,H//2),(W//2+8,H//2),2);pygame.draw.line(screen,(245,245,245),(W//2,H//2-8),(W//2,H//2+8),2);self.ui()
 def ui(self):
  # bars
  pygame.draw.rect(screen,(25,25,25),(18,18,230,22));pygame.draw.rect(screen,(190,45,55),(20,20,226*max(0,self.p.hp)/20,18));pygame.draw.rect(screen,(25,25,25),(18,45,230,22));pygame.draw.rect(screen,(220,155,40),(20,47,226*max(0,self.p.food)/20,18))
  screen.blit(small.render(f'HP {self.p.hp:.0f}  FOOD {self.p.food:.0f}',True,(255,255,255)),(25,47))
  # hotbar
  size=min(64,W//10); total=size*len(HOT);x=(W-total)//2;y=H-size-20
  for i,b in enumerate(HOT):
   r=pygame.Rect(x+i*size,y,size-4,size-4);pygame.draw.rect(screen,(230,190,70) if i==self.p.sel else (35,35,40),r);pygame.draw.rect(screen,(210,210,210),r,2);pygame.draw.rect(screen,COL[b],r.inflate(-22,-22));n=self.p.inv.get(b,0);screen.blit(small.render(str(n),True,(255,255,255)),(r.x+4,r.bottom-19))
  # mobile controls
  alpha=110; overlay=pygame.Surface((W,H),pygame.SRCALPHA)
  for name,(x,y,r) in {'L':(90,H-120,65),'R':(220,H-120,65),'J':(W-95,H-105,55),'M':(W-95,H-220,55),'P':(W-210,H-105,55),'I':(W-210,H-220,55)}.items():
   pygame.draw.circle(overlay,(255,255,255,alpha),(x,y),r);t=font.render(name,True,(20,20,20));overlay.blit(t,t.get_rect(center=(x,y)))
  screen.blit(overlay,(0,0))
  if self.inv_open or self.craft_open:
   panel=pygame.Rect(W*.12,H*.12,W*.76,H*.65);pygame.draw.rect(screen,(24,24,28),panel);pygame.draw.rect(screen,(180,180,190),panel,3);title='INVENTORY' if self.inv_open else 'CRAFTING';screen.blit(big.render(title,True,(255,255,255)),(panel.x+20,panel.y+15))
   if self.craft_open:
    yy=panel.y+80
    for name,ing,res in RECIPES:
     txt=name+'  '+', '.join(f'{NAME.get(k,k)}x{v}' for k,v in ing.items());pygame.draw.rect(screen,(50,50,55),(panel.x+20,yy,panel.w-40,42));screen.blit(small.render(txt,True,(235,235,235)),(panel.x+30,yy+12));yy+=52
   else:
    xx=panel.x+25;yy=panel.y+80
    for b,n in self.p.inv.items():screen.blit(small.render(f'{NAME[b]}: {n}',True,(240,240,240)),(xx,yy));yy+=28
 def block_target(self):
  # forward ray
  sy,cy=math.sin(self.p.yaw),math.cos(self.p.yaw); cp,sp=math.cos(self.p.pitch),math.sin(self.p.pitch)
  for i in range(1,80):
   t=i*.08; x=self.p.x+sy*cp*t; y=self.p.y+sp*t;z=self.p.z-cy*cp*t;pos=(math.floor(x),math.floor(y),math.floor(z));b=self.world.get(*pos)
   if b not in (B.AIR,B.WATER):return pos,b
  return None,None
 def mine(self):
  pos,b=self.block_target()
  if not pos:return
  if self.p.breaking!=pos:self.p.breaking=pos;self.p.progress=0
  power={'hand':1,'wood_pick':2,'stone_pick':3,'iron_pick':5}.get(self.p.tool,1);self.p.progress+=power/max(1,HARD.get(b,1))
  if self.p.progress>=15:
   self.world.set(*pos,B.AIR);drop=DROP.get(b,b);self.p.inv[drop]=self.p.inv.get(drop,0)+1;self.p.breaking=None;self.p.progress=0
 def place(self):
  pos,b=self.block_target()
  if not pos:return
  x,y,z=pos;sy,cy=math.sin(self.p.yaw),math.cos(self.p.yaw); cp,sp=math.cos(self.p.pitch),math.sin(self.p.pitch);tx=self.p.x+sy*cp*2.8;ty=self.p.y+sp*2.8;tz=self.p.z-cy*cp*2.8;target=(math.floor(tx),math.floor(ty),math.floor(tz));hb=HOT[self.p.sel]
  if self.p.inv.get(hb,0)>0 and self.world.get(*target)==B.AIR:self.world.set(*target,hb);self.p.inv[hb]-=1
 def craft(self,idx):
  if not 0<=idx<len(RECIPES):return
  _,ing,res=RECIPES[idx]
  if all(self.p.inv.get(k,0)>=v for k,v in ing.items() if isinstance(k,B)) and all(self.p.inv.get(k,0)>=v for k,v in ing.items() if isinstance(k,str)):
   for k,v in ing.items():self.p.inv[k]-=v
   for k,v in res.items():
    if isinstance(k,B):self.p.inv[k]=self.p.inv.get(k,0)+v
    elif k=='tool':self.p.tool=v
 def save(self):self.world.save(self.p);self.last_save=time.time()
 def events(self):
  for e in pygame.event.get():
   if e.type==pygame.QUIT: self.save();return False
   if e.type==pygame.KEYDOWN:
    if e.key==pygame.K_ESCAPE:self.menu=not self.menu
    if e.key==pygame.K_e:self.inv_open=not self.inv_open;self.craft_open=False
    if e.key==pygame.K_c:self.craft_open=not self.craft_open;self.inv_open=False
    if e.key==pygame.K_SPACE and self.p.ground:self.p.vy=7
    if pygame.K_1<=e.key<=pygame.K_9:self.p.sel=e.key-pygame.K_1
    if e.key==pygame.K_f:self.place()
   if e.type==pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0] and not (self.inv_open or self.craft_open):self.p.yaw+=e.rel[0]*.004;self.p.pitch=max(-1.2,min(1.2,self.p.pitch-e.rel[1]*.004))
   if e.type==pygame.MOUSEBUTTONDOWN:
    if e.button==1:self.mine()
    if e.button==3:self.place()
  return True
 def run(self):
  while True:
   dt=min(.05,clock.tick(60)/1000); 
   if not self.events():break
   keys=pygame.key.get_pressed()
   if not self.inv_open and not self.craft_open and not self.menu:self.p.update(self.world,dt,keys);[m.update(self.world,self.p,dt) for m in self.mobs];self.world.time+=dt
   if time.time()-self.last_save>20:self.save()
   self.render();pygame.display.flip()
  pygame.quit()

if __name__=='__main__':Game().run()
