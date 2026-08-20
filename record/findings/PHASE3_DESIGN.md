# PHASE 3 — THE KNOWLEDGE FABRIC AND THE IDEA ECONOMY

**2026-08-10, on `v4-cold`. Isaiah's directives: Phase 3 goes; three knowledge streams
(collective / personal / kin); NO database — a pure-Python, Kaggle-portable store; carry the
v3/v4 transfer features so agents never start from zero; the viral idea economy (rewarded good
ideas, pariah-marked bad ones) is paramount.**

---

## 1. THE KAGGLE FACT (verified, not assumed)

There is **no live shared "sys area"** across running Kaggle instances. The real mechanism:
files written to `/kaggle/working` persist only as committed notebook output; other
sessions/notebooks attach them (or a Dataset) read-only under `/kaggle/input`. So the portable
shape is exactly: **seed knowledge mounted read-only + session knowledge written locally +
merged at load**. No server, no daemon, no SQLite required.

## 2. THE KNOWLEDGE FABRIC (pure Python, file-backed, no DB)

`engines/egocentric/fabric.py` — stdlib only (json/os/io). A fabric is a DIRECTORY of
append-only JSONL streams:

    <root>/collective/<topic>.jsonl          all agents, all games (v4's "collective database")
    <root>/personal/<agent_id>/<topic>.jsonl one agent's own stream
    <root>/kin/<kin_key>/<topic>.jsonl       the stream of agents LIKE this one (lineage/role)

API: `append(scope, topic, record)` (crash-safe line append; deterministic per-stream sequence
numbers, no wall-clock in the default path), `query(scope, topic, where=..., limit=...)`,
`scopes()`. **Overlay**: `KnowledgeFabric(root, seeds=[dir, ...])` — seed directories are
read-only (the `/kaggle/input` pattern); queries merge seeds+local; appends go local only. A
corrupt trailing line (crash mid-write) is skipped on load, never fatal.

## 3. THE IDEA ECONOMY ON THE FABRIC (the viral/pariah machinery, done consumably)

v4's version was measured on the iced branch: pariah storage existed with NO consumer, and the
lessons pipeline was stranded on the abandoned loop stack. This version is built consumer-first:

- **MINT** (`mint(idea, by, game)`): only on SIGNAL (a real level-up — the wheel rule extends
  to memory: the mint compounds nothing on silence). An idea = a generator, never playback:
  confirmed goal relation, established action→delta map entries, game-feature observations.
- **ECHO** (`echo(idea_id, by)`): an independent re-confirmation (another episode/agent's
  level-up while using the idea) → credibility up → **the ORIGIN agent's reputation up — the
  viral reward.** Good ideas pay their authors.
- **FALSIFY** (`falsify(idea_id, by)`): pursued, reached, no reward → pariah mark. Defeasible:
  down-ranked hard, never deleted (the adaptive-immune rule from the newhorse GoalManager).
- **PRIORS** (`priors(game, agent_id, kin_key)`): merged collective+kin+personal ideas ranked
  by credibility, pariahs at the bottom — what a fresh agent loads so it does NOT start from
  zero. Personal outranks kin outranks collective at equal credibility (nearest evidence wins).

## 4. TRANSFER SEMANTICS (the wheel rule applied to inherited knowledge)

A seeded idea with confirmed-by-reward provenance counts as SIGNAL (someone's real level win)
— it may open the drive gate, but at a REDUCED inherited price (below a same-episode
confirmation) and defeasibly: one reached-without-reward event falsifies it back to pariah.
Playback (`winning_sequences`) stays in stock v4 untouched — the fabric carries GENERATORS
only. **[FLAGGED FOR ISAIAH'S VETO: inherited confirmations opening the wheel at reduced
price — the alternative is priors bias proposal order only and never drive.]**

## 5. WHAT CARRIES OVER FROM v3/v4 (the features that helped transfer)

| v4 feature | fabric equivalent |
|---|---|
| winning_sequences replay | stays in stock (playback layer, untouched) |
| viral_information_packages | MINT + ECHO + reputation (consumer-first this time) |
| lessons→pariah pipeline (stranded in v4) | FALSIFY + pariah ranking (wired, gated) |
| learned_game_mechanics / universal_patterns | minted generator ideas per game + cross-game topics |
| curriculum/level transfer | priors loaded at episode start; level-up mints updated ideas |

## 6. STOCK v4'S SQLITE

Keeps running untouched underneath (it IS stock v4's organ; ripping it out would destroy the
baseline). The fabric is the NEW layer's only store and the only thing that ports to Kaggle.
