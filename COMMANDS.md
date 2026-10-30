# TransferGap: every command you need (copy, paste, in this order)

All paths are relative to `lane-b-human-demo/transfergap` unless a line says otherwise. Cluster = GPU cluster WZL, namespace `isaac-sim`, VPN must be on.
Never print `Physical AI/transfergap/.env` (it holds the Token Factory key) and never put the kubeconfig in git.

## 0. Once per terminal
```bash
export PATH=$PATH:~/.local/bin          # kubectl lives here
kubectl auth whoami                      # proves the VPN and kubeconfig work
kubectl get deploy,pods -n isaac-sim     # what is running; tg-dev 1/1 means it is holding the GPU
```

## 1. Turn the GPU box ON / OFF  (do OFF whenever you are not running a GPU job: the card is shared)
```bash
# ON
kubectl scale deploy/tg-dev -n isaac-sim --replicas=1
kubectl rollout status deploy/tg-dev -n isaac-sim
P=$(kubectl get pods -n isaac-sim -l app=tg-dev -o name | head -1 | cut -d/ -f2); echo $P
kubectl cp docker/cluster/restore_tg_dev.sh isaac-sim/$P:/ws/transfergap/runs/restore_tg_dev.sh
kubectl exec -n isaac-sim $P -- bash /ws/transfergap/runs/restore_tg_dev.sh     # REQUIRED after every ON (reinstalls pod-local tools)

# check the GPU
kubectl exec -n isaac-sim $P -- nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader

# OFF  (frees the L40S; files on the volume /ws/transfergap are kept)
kubectl scale deploy/tg-dev -n isaac-sim --replicas=0
kubectl get pods -n isaac-sim            # tg-dev must be gone; Completed/Error job pods hold no GPU
```
Only ONE of {tg-dev, a GPU Job} can hold the card: scale tg-dev to 0 before applying any GPU Job below, and back to 1 afterwards (then the restore line).

## 2. The one-command demo (video -> measurements -> robots -> G1 -> video), in the container image
```bash
kubectl scale deploy/tg-dev -n isaac-sim --replicas=0
# edit docker/cluster/showcase-job.yaml first: a NEW job name (e.g. tg-showcase-r7) and a NEW --out folder, and --shoulder-width-m (derived 0.44 until you measure)
kubectl apply -f docker/cluster/showcase-job.yaml
kubectl logs -f job/tg-showcase-r6 -n isaac-sim            # use the job name from the yaml
kubectl get job -n isaac-sim                                # Complete / Failed
```
Result files land in `/ws/transfergap/<out folder>` on the volume. Read them back with the pod (section 1 ON), e.g.
`kubectl cp isaac-sim/$P:/ws/transfergap/showcase_out_r6/TransferGap_demo_v2.mp4 ./demo.mp4`

## 3. Build and publish a new image (about 16 + 8 minutes, no GPU needed)
```bash
cd .. && bash transfergap/docker/build_context.sh /tmp/ctx && tar -C /tmp/ctx -czf /tmp/ctx.tgz transfergap && cd transfergap    # committed code only
kubectl cp /tmp/ctx.tgz isaac-sim/$P:/ws/transfergap/ctx_unified_r7.tgz
kubectl exec -n isaac-sim $P -- bash -c 'cd /ws/transfergap && mkdir -p ctx_unified_r7 && tar -xzf ctx_unified_r7.tgz -C ctx_unified_r7 --strip-components=1'
# copy docker/cluster/kaniko-full-r6.yaml and skopeo-push-ghcr-r6.yaml to r7 (names, ctx path, tar name, tag), then:
kubectl apply -f docker/cluster/kaniko-full-r7.yaml
kubectl apply -f docker/cluster/skopeo-push-ghcr-r7.yaml
```

## 4. Cosmos critic on new rollouts (needs tg-dev ON + restore)
```bash
# render labelled clips of a demo (CPU, ~1 min), then score with Cosmos-Reason2-2B zero-shot and the adapter (~3 min)
kubectl exec -n isaac-sim $P -- bash -c 'cd /ws/transfergap/ctx_unified_r6 && export MUJOCO_GL=egl PYTHONPATH=. && /ws/transfergap/envs/render/bin/python -m transfergap.sim.critic_new_rollouts --demo /ws/transfergap/demos/newdemo_r6.npz --out /ws/transfergap/critic_new_r6 --seeds 1000-1059 --workers 16'
kubectl exec -n isaac-sim $P -- bash -c 'cd /ws/transfergap/ctx_unified_r6/transfergap/demo/tools && export HF_HOME=/ws/transfergap/cache/huggingface HF_HUB_OFFLINE=1 && /ws/transfergap/envs/cosmos/bin/python cosmos_critic_eval.py --data /ws/transfergap/critic_new_r6 --adapter /ws/transfergap/runs/cosmos_critic_adapter --out /ws/transfergap/critic_new_r6_eval'
```

## 5. Nemotron diagnosis loop (Nebius Token Factory; simulation on the cluster, the key stays on your laptop)
```bash
set -a; . "../../Physical AI/transfergap/.env"; set +a        # loads the key into this shell only; never echo it
python3 live/agent_loop_cluster.py --demo-remote /ws/transfergap/demos/newdemo_r6.npz --demo-local /tmp/nd/newdemo_r6.npz --robots ur5e ur10e --max-rounds 4
# results: results/demo_agent_loop_<tag>.json and results/demo_budget_v1_<tag>_<robot>*/
```

## 6. Pose estimators
```bash
# Fast SAM 3D Body (installed already; env /ws/transfergap/envs/fsam). Smoke test, then compare with the pipeline:
kubectl exec -n isaac-sim $P -- bash /ws/transfergap/envs/fsam_smoke.sh 30
kubectl exec -n isaac-sim $P -- bash /ws/transfergap/envs/fsam_compare.sh
kubectl exec -n isaac-sim $P -- bash /ws/transfergap/envs/fsam_objheight.sh      # the object-height finding (lowest_hand vs hand_at_grasp)
# pipeline by hand, any joints file (inside the pod, render env):
#   python -m transfergap.pipeline --joints J.npz --window A B --events G R --object-height lowest_hand|hand_at_grasp --shoulder-width-m 0.44 --robots ur5e ur10e kairos --out DIR
```

## 7. The demo UI (no cluster needed)
```bash
python3 ui_demo/build.py                 # rebuild data.js from the committed result files
bash ui_demo/fetch_media.sh              # copy videos from the cluster (needs tg-dev ON)
python3 ui_demo/serve.py 8765            # then open http://127.0.0.1:8765/   (press P for presentation mode)
```

## 8. Tests and git
```bash
PYTHONPATH=. python3 -m unittest discover -s tests -q     # full suite (some tests skip without assets)
git log --oneline | head                                  # branch lane-b/human-demo; commit message rule: no assistant names or co-author trailers
```

## 9. When something breaks
- `kubectl` times out or "connection reset": the VPN link drops often. Retry; for big uploads use small pieces and resume (see `/tmp/fsam_ckpt/push.sh` pattern: 64 MB pieces, append only missing bytes).
- Pod Pending: both L40S are busy; `kubectl describe pod <pod> -n isaac-sim` and read Events.
- After a scale 0 -> 1 nothing works: you forgot the restore line in section 1.
- Never `kubectl delete` anything on the volume or `rm -rf` under `/ws/transfergap` without a verified backup.
