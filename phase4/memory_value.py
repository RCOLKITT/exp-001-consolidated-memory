"""Memory Value Report: per-repo read-out of one rolling arms.json (file level).

Exploratory tooling, not part of any registered analysis. Prints hit@3 / false-positive
rate per arm, paired wins/losses vs control, control precision by rank, the show-top-k
display-policy table, repeated false positives, and hit rate split by gold recurrence.
Writes <arms>.mvr.json next to the input.

    python -m phase4.memory_value results/experiment/23/rolling/rcolkitt__vasperamemory.arms.json
"""
import json,sys,collections,os
path=sys.argv[1]
d=json.load(open(path))
gold=d['gold']; arms=d['arms']
def fkey(loc): return loc.split('::')[0]
tasks=[t for t in gold if t in arms['control']['flags']]
print('granularity',d.get('granularity'),'mode',d.get('mode'),'tasks scored',len(tasks),'gold n',len(gold))
print('errors',len(d.get('errors',{})),'learn_errors',len(d.get('learn_errors',{})))
out={'n_tasks':len(tasks),'arms':{}}
for name,a in arms.items():
    fl=a['flags']; hits=0; nflag=0; fp=0; ret=0
    for t in tasks:
        g={fkey(x) for x in gold[t]}; f=[fkey(x) for x in fl.get(t,[])]
        hits+=any(x in g for x in f); nflag+=len(f); fp+=sum(x not in g for x in f)
    ret=sum(1 for t in tasks if a.get('retrieved',{}).get(t)) if isinstance(a.get('retrieved'),dict) else a.get('retrieved')
    m=dict(hit3=hits/len(tasks), fp_rate=(fp/nflag if nflag else None), n_flags=nflag, flags_per_task=nflag/len(tasks), retrieved=ret)
    out['arms'][name]=m; print(f"{name:12s} hit@3={m['hit3']:.3f} fp={m['fp_rate']:.3f} flags/task={m['flags_per_task']:.2f} retrieved={ret}")
# lift vs control with paired counts
c=arms['control']['flags']
for name,a in arms.items():
    if name=='control': continue
    w=l=0
    for t in tasks:
        g={fkey(x) for x in gold[t]}
        hc=any(fkey(x) in g for x in c.get(t,[])); ha=any(fkey(x) in g for x in a['flags'].get(t,[]))
        w+=(ha and not hc); l+=(hc and not ha)
    print(f"  {name} vs control: wins {w} losses {l} delta {100*(w-l)/len(tasks):+.1f} pts"); out['arms'][name]['wins']=w; out['arms'][name]['losses']=l
# precision by rank (control), dedup files within a task's list keeping first position
prec=collections.defaultdict(lambda:[0,0]); first_hit_rank=collections.Counter()
for t in tasks:
    g={fkey(x) for x in gold[t]}; seen=set(); r=0; fh=None
    for x in c.get(t,[]):
        f=fkey(x)
        if f in seen: continue
        seen.add(f); r+=1
        prec[r][1]+=1; ok=f in g; prec[r][0]+=ok
        if ok and fh is None: fh=r
    first_hit_rank[fh]+=1
print('precision by rank (control, file):',{r:(round(v[0]/v[1],3),v[1]) for r,v in sorted(prec.items())})
print('first correct at rank:',dict(first_hit_rank))
out['precision_by_rank']={r:[v[0],v[1]] for r,v in sorted(prec.items())}; out['first_hit_rank']={str(k):v for k,v in first_hit_rank.items()}
# display policy table: show top-k => hit rate, wrong pointers per task
for k in (1,2,3):
    h=0; wrong=0
    for t in tasks:
        g={fkey(x) for x in gold[t]}; seen=[]
        for x in c.get(t,[]):
            f=fkey(x)
            if f not in seen: seen.append(f)
        top=seen[:k]; h+=any(f in g for f in top); wrong+=sum(f not in g for f in top)
    print(f'show top-{k}: hit {h/len(tasks):.3f}, wrong pointers/task {wrong/len(tasks):.2f}')
    out[f'show{k}']=dict(hit=h/len(tasks),wrong_per_task=wrong/len(tasks))
# directory-level hit for control
dh=0
for t in tasks:
    g={os.path.dirname(fkey(x)) for x in gold[t]}; dh+=any(os.path.dirname(fkey(x)) in g for x in c.get(t,[]))
print('control dir-level hit@3',round(dh/len(tasks),3)); out['dir_hit3']=dh/len(tasks)
# repeated false positives in control (candidates for veto)
fpc=collections.Counter(); tpc=collections.Counter()
for t in tasks:
    g={fkey(x) for x in gold[t]}
    for f in {fkey(x) for x in c.get(t,[])}: (tpc if f in g else fpc)[f]+=1
print('control top false-positive files:',[(f,n,tpc[f]) for f,n in fpc.most_common(8)])
out['top_fp']=[(f,n,tpc[f]) for f,n in fpc.most_common(8)]
# control hit split by whether any gold file had appeared in an earlier task's gold (recurrence)
order=list(gold.keys()); seen=set(); rec_hit=[0,0]; new_hit=[0,0]
for t in order:
    g={fkey(x) for x in gold[t]}
    if t in c:
        hit=any(fkey(x) in g for x in c[t]); (rec_hit if g&seen else new_hit)[0]+=hit; (rec_hit if g&seen else new_hit)[1]+=1
    seen|=g
print('control hit on recurring-gold tasks',rec_hit,'on novel-gold tasks',new_hit); out['rec_hit']=rec_hit; out['new_hit']=new_hit
json.dump(out,open(os.path.splitext(path)[0]+'.mvr.json','w'),indent=1)
