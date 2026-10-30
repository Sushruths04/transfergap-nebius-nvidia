import json, sys, math, random, hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'transfergap'))
from transfergap.metrics import score_episode
from g1.score import to_episode

out = {'reviewed_commit': '4150a34', 'mismatches': [], 'gap': {}, 'table': {}, 'g1_style': {}, 'g1_closed': {}}
def check(file, label, expected, found):
    if expected != found:
        out['mismatches'].append({'file': str(file), 'label': label, 'expected': expected, 'found': found})

def read_scores(file, seeds):
    groups, style = defaultdict(dict), defaultdict(list)
    with file.open() as f:
        for line in f:
            ep = json.loads(line)
            c, s = ep['condition'], ep['seed']
            if s in groups[c]:
                raise ValueError(f'Duplicate {file} {c} {s}')
            groups[c][s] = int(score_episode(ep)['success'])
            if 'style' in ep:
                style[c].append(ep['style']['path_rmse_mean_m'])
    for c, data in groups.items():
        assert set(data) == set(seeds), (file, c, sorted(data))
    return {c: np.array([d[s] for s in seeds]) for c,d in groups.items()}, style

summary = json.loads((root/'transfergap/results/gap_budget_v3/summary.json').read_text())
for robot in ['ur5e','ur10e']:
    file = root/f'transfergap/runs/gap_budget_v3/{robot}.jsonl'
    scores, _ = read_scores(file, range(3000,3500))
    full = scores['full']; rng = np.random.default_rng(12345)
    def stat(values):
        idx = rng.integers(0,500,size=(5000,500))
        return {'delta_pp': 100*float(values.mean()), 'ci95_pp': list(100*np.quantile(values[idx].mean(axis=1),[.025,.975]))}
    row = {'full':int(full.sum()),'conditions':{c:int(v.sum()) for c,v in scores.items()},'budgets':{},'corrections':{}}
    a = summary['arms'][robot]
    check(file.relative_to(root),'full',a['full_successes'],row['full'])
    singles=[]
    for comp in ['perception','retargeting','calibration','timing']:
        v=scores['oracle_'+comp]-full; singles.append(v)
        st=stat(v);row['budgets'][comp]=st
        for k in st:check('transfergap/results/gap_budget_v3/summary.json',robot+'/'+comp+'/'+k,a['budget_pp'][comp][k],st[k])
    allv=scores['oracle_all']-full
    row['oracle_all']=stat(allv)
    row['interaction']=stat(sum(singles)-allv)
    for key, source in [('oracle_all','oracle_all_pp'),('interaction','interaction_pp')]:
        for k in row[key]:
            sk='sum_minus_all_pp' if key=='interaction' and k=='delta_pp' else k
            check('transfergap/results/gap_budget_v3/summary.json',robot+'/'+key+'/'+k,a[source][sk],row[key][k])
    for name in ['look_again','ik_resolve','touch_probe_calibration','speed_cap_3']:
        c='full+'+name
        st=stat(scores[c]-full);st['successes']=int(scores[c].sum());row['corrections'][name]=st
        for k in st:check('transfergap/results/gap_budget_v3/summary.json',robot+'/'+name+'/'+k,a['corrections'][name][k],st[k])
    out['gap'][robot]=row
    print('gap',robot,row,flush=True)

v5=json.loads((root/'transfergap/results/demo_generalization_v5/summary.json').read_text())['runs']
for cell in ['A_pexels_8135753_notebook','A_pexels_8135753_markers','A_pexels_8135753_orange_marker','A_pexels_8135753_notepad','A_woman','B_woman','Own']:
    out['table'][cell]={}
    for robot in ['ur5e','ur10e']:
        file = root/f'transfergap/runs/demo_generalization_v5/{cell}/episodes_{robot}.jsonl' if cell!='Own' else root/f'transfergap/results/user_demo_v1/episodes_{robot}.jsonl'
        scores,style=read_scores(file,range(1000,1060))
        raw,stack=scores['raw'],scores['all_fixes']
        diff=stack-raw;rng=random.Random(0)
        samples=sorted(100*sum(rng.choices(list(map(int,diff)),k=60))/60 for _ in range(2000))
        row={'raw':int(raw.sum()),'stack':int(stack.sum()),'n':60,'gain_pp':100*float(diff.mean()),'ci95_pp':[samples[int(.025*1999)],samples[int(.975*1999)]], 'path_rmse_cm': {c:100*float(np.mean(s)) for c,s in style.items()}}
        out['table'][cell][robot]=row
        expected = v5[cell][robot] if cell!='Own' else json.loads((root/'transfergap/results/user_demo_v1/repro_summary.json').read_text())['robots'][robot]
        for k in ['raw','stack']:
            exp=expected[k] if cell!='Own' else expected['conditions']['raw' if k=='raw' else 'all_fixes']['successes']
            check(file.relative_to(root),k,exp,row[k])
    print('table',cell,out['table'][cell],flush=True)

def tier(ep):
    s=ep['states']; z0=s[0]['object_xyz'][2]
    return [int(any(x['hand_block_contact'] for x in s)),int(any(x['hand_block_contact'] and x['object_xyz'][2]-z0>=ep['task']['min_lift_m'] for x in s)), int(score_episode(ep)['success'])]

for run in ['g1_style_v1','g1_style_in_image_v1']:
    out['g1_style'][run]={}
    a=json.loads((root/f'transfergap/results/{run}/summary.json').read_text())['conditions']
    for c in ['style_human_pace','style_speed_cap_3','style_nominal_pace']:
        file=root/f'transfergap/results/{run}/episodes_{c}.jsonl'
        seen=set();counts=np.zeros(3,dtype=int)
        for l in file.open():
            ep=json.loads(l);identity=(ep['seed'],ep['rollout']);assert identity not in seen;seen.add(identity);counts+=tier(ep)
        assert seen=={(s,r) for s in range(100,110) for r in range(3)}
        row=dict(zip(['touch','grasp','place'],map(int,counts)));row['rollouts']=30;row['unique_seeds']=10
        out['g1_style'][run][c]=row
        for k in ['touch','grasp','place']:check(file.relative_to(root),k,a[c][k+'_rollout_rate']['k'],row[k])
    # Independently reconstruct the normalized episodes from the original 50 Hz logs too.
    raw_root = root / 'transfergap/runs' / ('g1_style' if run == 'g1_style_v1' else 'g1_style_img')
    for c, folder in [('style_human_pace','g1_style_human'), ('style_speed_cap_3','g1_style_cap3'), ('style_nominal_pace','g1_style_nominal')]:
        seen = set(); counts = np.zeros(3,dtype=int)
        for file in sorted((raw_root / folder).glob('*.episode.json')):
            raw = json.loads(file.read_text()); identity = (raw['seed'],raw['rollout'])
            assert identity not in seen; seen.add(identity)
            counts += tier(to_episode(raw,c,'perception',{}))
        assert seen == {(s,r) for s in range(100,110) for r in range(3)}
        for k, value in zip(['touch','grasp','place'],counts):
            check(str(file.parent.relative_to(root)), k, out['g1_style'][run][c][k], int(value))
        out['g1_style'][run][c]['original_raw_log_recount_matches'] = True
    print(run,out['g1_style'][run],flush=True)

# Raw logs recovered locally; the committed summaries are used only for comparison.
pack=Path(sys.argv[1]);meta=json.loads((pack/'plans/cl_seed1200.json').read_text())
a=json.loads((root/'transfergap/results/g1_in_image_v1/summary.json').read_text())
for setup in ['host','img']:
    counts=np.zeros(3,dtype=int);places={}; hashes={}
    for file in sorted((pack/setup).glob('*.episode.json')):
        raw=json.loads(file.read_text());seed=raw['seed'];assert seed not in places
        ep=to_episode(raw,setup,'none',meta);t=tier(ep);counts+=t;places[seed]=t[2];hashes[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    assert set(places)==set(range(1200,1240))
    row=dict(zip(['touch','grasp','place'],map(int,counts)));row['n']=40;row['places_by_seed']=places;row['raw_sha256']=hashes
    out['g1_closed'][setup]=row
    for k in ['touch','grasp','place']:check('transfergap/results/g1_in_image_v1/summary.json',setup+'/'+k,a[k+('_host' if setup=='host' else '_in_image')],row[k])
host,img=out['g1_closed']['host']['places_by_seed'],out['g1_closed']['img']['places_by_seed']
b=sum(img[s] and not host[s] for s in host);c=sum(host[s] and not img[s] for s in host)
out['g1_closed']['discordant']=[b,c];out['g1_closed']['mcnemar_exact']=min(1,2*sum(math.comb(b+c,k) for k in range(min(b,c)+1))/2**(b+c))
print('closed', {k:{x:y for x,y in v.items() if x not in ['places_by_seed','raw_sha256']} if isinstance(v,dict) else v for k,v in out['g1_closed'].items()},flush=True)
D=root/'transfergap/results/g1_in_image_v1'
def grasps(rows):
    rows=[r for r in rows if 1200<=r['seed']<=1209];assert sorted(r['seed'] for r in rows)==list(range(1200,1210));return sum(r['lift_cm']>=5 for r in rows)
host=[grasps(json.loads((root/'transfergap/results/g1_pelvis_drift_v1/rows.json').read_text()))]+[grasps(json.loads((D/f).read_text())) for f in ['rows_host_fresh_pod_1200_1209.json','rows_host_no_cached_engine_1200_1209.json','rows_host_sameday_v2_1200_1209.json','rows_host_sameday_v3_1200_1209.json']]
img=[grasps(json.loads((D/f).read_text())) for f in ['rows_image_hostlike_cpu_1200_1209.json','rows_image_deployment_pod_1200_1209.json','rows_image_hostlike_cuda_libs_1200_1209.json','rows_image_host_binaries_1200_1209.json']]+[grasps([r for f in ['rows_seeds_1200_1202.json','rows_seeds_1203_1239.json'] for r in json.loads((D/f).read_text())])]
out['g1_pooled']={'host':host,'image':img,'host_total':sum(host),'image_total':sum(img),'attempts_per_setup':50,'unique_seeds':10,'note':'Lift-only recount from diagnostic rows, not an independent raw-log grasp/contact recount.'}
print('pooled',out['g1_pooled']);print('mismatches',out['mismatches'])
destination = Path(sys.argv[2]) if len(sys.argv) > 2 else root / 'paper/review_recount.json'
destination.write_text(json.dumps(out,indent=2))
