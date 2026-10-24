import MetaTrader5 as m, numpy as np, sys, os, time
from datetime import datetime, timezone
m.initialize()
SYMS=sys.argv[1].split(",")
TFS={"M15":(m.TIMEFRAME_M15,40000),"H1":(m.TIMEFRAME_H1,20000),"D1":(m.TIMEFRAME_D1,3000)}
for s in SYMS:
    m.symbol_select(s,True)
    for n,(tf,cnt) in TFS.items():
        f=f"data/{s}_{n}.npy"
        if os.path.exists(f): continue
        t0=time.time(); r=None
        c=cnt
        while c>=1000:
            r=m.copy_rates_from_pos(s,tf,1,c)
            if r is not None and len(r): break
            c//=2
        if r is None: print(s,n,"none",m.last_error(),flush=True); continue
        np.save(f,r)
        print(s,n,len(r),datetime.fromtimestamp(int(r[0]['time']),timezone.utc).date(),"medspr",np.median(r['spread']),f"{time.time()-t0:.0f}s",flush=True)
