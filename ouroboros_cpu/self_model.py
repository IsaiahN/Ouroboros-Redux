"""self_model.py — discover the agent's LOCUS OF AGENCY from (prev, action, cur) transitions.
The agency core-knowledge prior (metalanguage Layer 4): the self is the coherently-controllable region of
the observation. Composed from THIS game's observations only (session-local -> passes the amnesia test; no
cross-game locus). GENERAL (any grid + any discrete actions) -> a pure module, not env-specific. A
coverage/nav planner uses locus() + move_map to have a position and a displacement model to plan over.
"""
import numpy as np

class SelfLocusModel:
    def __init__(self):
        self.locus=None            # (r,c) current estimate of the controllable locus
        self.move={}               # action -> mean (dr,dc) displacement of the locus
        self._n={}                 # action -> #observations
        self.controllable=set()    # actions that move the locus coherently
    def update(self, prev, action, cur):
        prev=np.asarray(prev); cur=np.asarray(cur)
        if prev.shape!=cur.shape: return
        ch=(prev!=cur)
        if not ch.any():
            self.move.setdefault(action,(0.0,0.0)); return     # no-op action: zero displacement
        rs,cs=np.where(ch); cen=(float(rs.mean()), float(cs.mean()))
        if self.locus is not None:
            d=(cen[0]-self.locus[0], cen[1]-self.locus[1])
            n=self._n.get(action,0); m=self.move.get(action,(0.0,0.0))
            self.move[action]=((m[0]*n+d[0])/(n+1),(m[1]*n+d[1])/(n+1)); self._n[action]=n+1
        self.locus=cen
    def agent_cell(self):
        return (int(round(self.locus[0])), int(round(self.locus[1]))) if self.locus is not None else None
    def coherent_actions(self, min_disp=0.5, min_n=2):
        """actions whose mean displacement is consistent and non-trivial = genuine MOVE actions."""
        out={}
        for a,(dr,dc) in self.move.items():
            if self._n.get(a,0)>=min_n and (abs(dr)+abs(dc))>=min_disp: out[a]=(dr,dc)
        return out

    def probe(self, adapter, k=4):
        """Controlled experiment (metalanguage: Known-Unknown -> design an experiment). For each action,
        reset to a fixed state and repeat it k times, measuring the CLEAN per-step displacement of the
        change-centroid. Isolates each action's effect (random mixing contaminates it). Builds move_map."""
        import numpy as np
        acts = adapter.actions() if hasattr(adapter,'actions') else []
        if not acts:
            g=adapter.reset(); acts=adapter.actions() if hasattr(adapter,'actions') else []
        for a in acts:
            g=adapter.reset(); cens=[]
            for _ in range(k):
                g2,_,d,_=adapter.step(a); ch=(np.asarray(g)!=np.asarray(g2))
                if ch.any():
                    rs,cs=np.where(ch); cens.append((float(rs.mean()),float(cs.mean())))
                g=g2
                if d: break
            if len(cens)>=2:
                deltas=[(cens[i+1][0]-cens[i][0], cens[i+1][1]-cens[i][1]) for i in range(len(cens)-1)]
                self.move[a]=(float(np.mean([x[0] for x in deltas])), float(np.mean([x[1] for x in deltas])))
                self._n[a]=len(deltas)
                if cens: self.locus=cens[-1]
            else:
                self.move[a]=(0.0,0.0); self._n[a]=k     # no-op
        adapter.reset()
        return self.coherent_actions()
