> **SUPERSEDED (2026-08-20): the accepted refactor plan's W5 is this document's successor.** The three correlation exclusions bind any marketplace mechanism. Kept in place because live code cites it by name; see `record/prereg/PREREG_REVIEW_2026-08-20.md`.

# PRE-REGISTRATION — THE MARKETPLACE MERGE (C33 step 1: every action carries a bet)

**Written 2026-08-12, at `73f8df0`+controls. The re-clearing price at per-action granularity —
the anti-hardening mechanism at its densest, and the room chain's admission substrate.**

## THE CHANGE THAT WILL BE AUTHORISED
> Port the iced branch's proven pricing spine (Ouroboros repo, `engines/economy/marketplace.py`
> at its final iced state — 89-line verbatim core + the settle machinery) into
> `engines/egocentric/` on v4-cold, adapted to the fabric (bets and settlements are fabric
> topics — the ledger the replay test needs). Per action: commit a prediction family (paste +
> transform members, exactly the iced final state), settle against the executed action's
> next frame. LAWS BAKED IN FROM COMMIT ONE: counterfactuals never priced (settle attribution);
> family-best recording (evidence added, never replaced); executed-action discipline. The wheel
> rule unchanged: bet scores inform proposal order and (later) room admission — they do NOT
> drive actions in this step (containment: byte-inert without consumers).

## THE GATE — binding
1. TESTS FIRST, SHOWN TO FAIL: the pricing core (Goodhart-guarded salience; no-change frames
   score match fraction); settle attribution (void on committed≠executed); family-best floor;
   fabric bet/settlement records with lineage fields (parent, priors consumed — ρ_deriv needs
   them from birth).
2. ⭐ FALSIFIER (containment): all six budget-restored control shas byte-identical (bets are
   recorded, nothing consumes them yet).
3. ⭐ FALSIFIER (capability): the band census RE-RUN on v4-cold — priced settles on ≥10 games
   with the in-band/out-of-band split reproduced in character (partial prediction exists where
   it existed before).
4. ⭐ FALSIFIER (debasement — the beat-104 receipt): NON-TRIVIAL settlement rate reported per
   game (n_changed > 0); high settlement volume with near-zero non-trivial rate on a game =
   pricing the board's inertia = the merge failing while looking successful. Reported, and any
   consumer built later must exclude trivial settles from its evidence.

## THE UNDO
`git revert` of the merge commit(s).
