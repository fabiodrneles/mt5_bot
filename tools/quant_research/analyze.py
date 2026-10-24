import json,sys,collections
r=json.load(open(sys.argv[1]))
print("configs",len(r))
# robustez: fracao de configs da mesma familia (sym,tf,strat) lucrativas nos DOIS periodos
fam=collections.defaultdict(list)
for x in r: fam[(x['sym'],x['tf'],x['strat'])].append(x)
print("\n== familias robustas (>=50% das variacoes lucram IS e OOS) ==")
fr=[]
for k,v in fam.items():
    ok=[x for x in v if x['IS']['net']>0 and x['OOS']['net']>0 and x['IS']['n']>=30 and x['OOS']['n']>=20]
    fr.append((len(ok)/len(v),k,len(v),sum(x['OOS']['net'] for x in v)/len(v)))
for f,k,n,avg in sorted(fr,reverse=True)[:25]:
    print(f"{k[0]:8}{k[1]:4}{k[2]:6} robust={f:.0%} de {n} | OOS medio ${avg:.2f}")
print("\n== melhores configs individuais (IS e OOS PF>=1.2, n>=30/20) ==")
good=[x for x in r if x['IS']['pf']>=1.2 and x['OOS']['pf']>=1.2 and x['IS']['n']>=30 and x['OOS']['n']>=20]
good.sort(key=lambda x:-x['OOS']['net']/max(x['yrs_oos'],0.1))
for x in good[:30]:
    I,O=x['IS'],x['OOS']
    print(f"{x['sym']:7}{x['tf']:4}{x['strat']:6}{str(x['par']):60} IS n{I['n']} pf{I['pf']} ${I['net']} | OOS n{O['n']} pf{O['pf']} ${O['net']} dd{O['dd']} worst{O['worst']} cl{O['maxcl']} /ano ${O['net']/x['yrs_oos']:.2f}")
