import sys, numpy as np, itertools, collections
from datetime import datetime, timezone
import research as R

def by_year(tr):
    y=collections.defaultdict(list)
    for t,dr,u,b in tr: y[datetime.fromtimestamp(int(t),timezone.utc).year].append(u)
    return " ".join(f"{k}:{sum(v):+.2f}({len(v)})" for k,v in sorted(y.items()))

def run(sym, tf, name, par, sprmult=1.0):
    d=R.load(sym,tf); d["spr"]=d["spr"]*sprmult
    for nm,p,sig,stop,tgt,xl,xs,mb,intra in R.strategies(d):
        if nm==name and p==par:
            tr=R.simulate(sym,d,sig,stop,tgt,xl,xs,mb,intra)
            return tr

cands=[("HK50","H4","PULLB",{'k':1.0,'R':2.0,'intra':False}),
       ("HK50","H4","PULLB",{'k':1.5,'R':2.0,'intra':False}),
       ("HK50","H4","PULLB",{'k':1.0,'R':3.0,'intra':True}),
       ("US500","D1","RSI2",{'L':5,'k':2.0,'longonly':False,'intra':False}),
       ("US500","D1","RSI2",{'L':10,'k':3.0,'longonly':True,'intra':False}),
       ("EU50","D1","RSI2",{'L':10,'k':2.0,'longonly':False,'intra':False}),
       ("UK100","H1","BBMR",{'dev':2.5,'k':1.5,'sma200':True,'intra':False}),
       ("HK50","H1","BBMR",{'dev':2.0,'k':1.5,'sma200':True,'intra':True})]
for c in cands:
    for sm in (1.0,1.5):
        tr=run(*c,sprmult=sm)
        s=R.stats(tr)
        print(f"{c[0]} {c[1]} {c[2]} {c[3]} spr x{sm}: {s}")
    print("   anos:",by_year(run(*c)))
