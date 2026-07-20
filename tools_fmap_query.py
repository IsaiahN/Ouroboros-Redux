"""Dogfood the FMap on REAL build problems: I reason each problem's F* coords (stage 0),
then rank the 46 real frameworks by the engine's own distance metric (stage 1)."""
import glob, yaml
DIMS=['resource_pressure','actor_complexity','information_asymmetry','coupling_tightness','time_pressure','boundary_permeability']
def dist(a,b): return (sum((a[d]-b[d])**2 for d in DIMS)/len(DIMS))**0.5
F={}
for f in glob.glob("/tmp/nb/ariadne/src/ariadne/kernel/*.yaml"):
    d=yaml.safe_load(open(f))
    if isinstance(d,dict) and "f_star_coordinates" in d:
        fc=d["f_star_coordinates"]
        if all(k in fc for k in DIMS):
            F[d.get("id")] = {"c":{k:float(fc[k]) for k in DIMS},"desc":d.get("description","")}
def query(name, coords, k=5):
    print("\n### PROBLEM: %s"%name)
    print("   my stage-0 F* estimate:", {d:coords[d] for d in DIMS})
    ranked=sorted(F, key=lambda fid: dist(coords,F[fid]["c"]))[:k]
    for i,fid in enumerate(ranked):
        print("   %d. %-34s (d=%.3f)  %s"%(i+1,fid,dist(coords,F[fid]["c"]),F[fid]["desc"][:70]))

# A) VALIDATION: the reject-memory problem (the map used the immune system / CRISPR for this)
query("re-tries dead approaches; needs a weighted, reopenable reject-memory",
      {'resource_pressure':0.9,'actor_complexity':0.5,'information_asymmetry':0.6,
       'coupling_tightness':0.3,'time_pressure':0.6,'boundary_permeability':0.7})
# B) OPEN: the new-horse marketplace pricing problem
query("many hypotheses with private evidence; pick which drives the next action, no central controller",
      {'resource_pressure':0.6,'actor_complexity':0.85,'information_asymmetry':0.8,
       'coupling_tightness':0.6,'time_pressure':0.6,'boundary_permeability':0.5})
