"""ASYMMETRIC-NORMALISATION SWEEP (Seat 4's proposal).
Where a helper normalises an input, does EVERY SIBLING input go through it?
The link-3 defect: _get_frame_array(pre) with post passed raw."""
import ast
import os
import re

PAIRS = [("pre","post"),("before","after"),("old","new"),("a","b"),
         ("prev","curr"),("prev","cur"),("src","dst"),("start","end"),("lhs","rhs")]
NORM = re.compile(r"^_?(get_\w*_array|normali[sz]e\w*|coerce\w*|as_\w+|to_\w+_array|_grid|_frame)\w*$")
FILES = ["cognitive_game_player.py","cognitive_loop.py"] + [
    os.path.join(r,f) for r,_,fs in os.walk("engines") for f in fs if f.endswith(".py")]
hits=[]
for path in FILES:
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except Exception:
        continue
    norms={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,)) and NORM.match(n.name)}
    if not norms:
        norms = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)]:
        # collect normaliser calls and their argument names
        called={}
        for c in ast.walk(fn):
            if isinstance(c,ast.Call):
                nm = c.func.attr if isinstance(c.func,ast.Attribute) else (c.func.id if isinstance(c.func,ast.Name) else "")
                if nm and NORM.match(nm) and c.args:
                    a=c.args[0]
                    an = a.id if isinstance(a,ast.Name) else (a.attr if isinstance(a,ast.Attribute) else None)
                    if an:
                        called.setdefault(nm, set()).add(an)
        for nm,args in called.items():
            names={a.lower() for a in args}
            def _tok(n):
                # WORD-BOUNDARY tokens, not substrings: 'predicted' must NOT match 'pre'.
                return {t for t in re.split(r"[^a-z0-9]+", n) if t}
            toks = set()
            for n in names:
                toks |= _tok(n)
            for x,y in PAIRS:
                hasx = x in toks
                hasy = y in toks
                if hasx ^ hasy:   # one side normalised, sibling not
                    present = x if hasx else y
                    missing = y if hasx else x
                    hits.append((path, fn.name, fn.lineno, nm, sorted(args), present, missing))
print("ASYMMETRIC NORMALISATION CANDIDATES")
print("NOTE: word-boundary tokens only; a helper that normalises both args internally is clean by construction and is not detectable from the call site.")
print("(a normaliser applied to one half of a known pair, sibling not seen)\n")
seen=set()
for h in hits:
    k=(h[0],h[1],h[3],h[5],h[6])
    if k in seen:
        continue
    seen.add(k)
    print(f"  {h[0]}:{h[2]}  in {h[1]}()")
    print(f"      normaliser {h[3]}() applied to {h[4]}  -> has '{h[5]}', MISSING '{h[6]}'")
print(f"\nCANDIDATES: {len(seen)}")
