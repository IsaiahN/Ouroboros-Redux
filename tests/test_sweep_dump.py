"""★ THE SIDECAR: A SWEEP THAT CAN BE RE-RENDERED IS A SWEEP THAT NEED NOT BE RE-RUN. ★

Every capture written before this beat is rendered TEXT. When a printer was found wrong -- and it has been
found wrong three times now (the re-added counter, the `empty` field carrying `raised`, and CLASSIFIER 18's
control grouping by exit before action) -- every reading ever taken through it had to be re-MEASURED, at the
price of a live sweep, because rendered text cannot be re-rendered. `tools/sweep_chain.py` persisted no result
JSON: `main()` printed straight to stdout and the dict died with the process.

So the sweep now writes `res` beside its capture. What is pinned here is NOT that a file appears -- a file that
reloads to different numbers is worse than no file, because it is a receipt that lies one file over. What is
pinned is the ROUND TRIP: dict -> JSON -> dict renders BYTE-IDENTICALLY to the dict the sweep measured.

The third test is the one that makes the other two mean anything. An equality assertion between two renders is
worthless unless the renders CAN differ, so a deliberately corrupted reload is asserted to be caught.
"""
import contextlib
import io
import json
import os
import sys

sys.path.insert(0, "tools")

from test_sweep_report import _N, _res_engaged, _run          # real receipts, never a hand-written dict


def _live_res():
    """Two games with DIFFERENT boards, so the sidecar is exercised on a result dict that actually varies: one
    board answers only to A1, the other answers to everything (the self-motion case). A round trip that flattened
    the per-game keying would pass on one game and fail here."""
    return _res_engaged(aa11=_run("aa11-aaaa", _N, ("A1",)),
                        bb22=_run("bb22-bbbb", _N, None))


def test_the_sidecar_reloads_to_a_byte_identical_render(tmp_path):
    """THE RECEIPT. If this holds, a printer fix after today is a re-render and not a sweep."""
    import sweep_chain
    res = _live_res()
    live = sweep_chain.render_to_string(res)
    path = sweep_chain.dump_res(res, str(tmp_path / "res.json"))
    with open(path) as fh:
        back = json.load(fh)
    assert sweep_chain.render_to_string(back) == live


def test_the_reload_carries_the_numbers_and_not_only_the_shape(tmp_path):
    """A render can match while the data underneath is thinner than it looks -- an empty section renders the same
    on every input. So the reloaded dict is checked for the two banked joints the whole `live` split is derived
    from, by NAME and by TOTAL, rather than only through the printer that reads them."""
    import sweep_chain
    res = _live_res()
    path = sweep_chain.dump_res(res, str(tmp_path / "res.json"))
    with open(path) as fh:
        back = json.load(fh)
    for gid in res["results"]:
        a = res["results"][gid]["engage"]["board"]
        b = back["results"][gid]["engage"]["board"]
        assert b["cells_hist"] == a["cells_hist"], gid       # keys are strings on both sides or this fails
        assert b["cells_hist_n"] == a["cells_hist_n"], gid
        assert b["live_hist"] == a["live_hist"], gid
        assert b["split"] == a["split"], gid


def test_a_corrupted_reload_is_CAUGHT_so_the_comparison_is_not_vacuous(tmp_path):
    """★ THE CONTROL. The two tests above assert that two renders agree; that is only evidence if they COULD
    disagree. Here one banked number is changed by one and the renders are required to differ -- if this passes
    trivially, the comparison in `main()` is decoration and the sidecar's verdict line means nothing."""
    import sweep_chain
    res = _live_res()
    live = sweep_chain.render_to_string(res)
    path = sweep_chain.dump_res(res, str(tmp_path / "res.json"))
    with open(path) as fh:
        back = json.load(fh)
    gid = sorted(back["results"])[0]
    back["results"][gid]["engage"]["board"]["steps"] += 1
    assert sweep_chain.render_to_string(back) != live


def test_the_render_path_opens_no_session_and_says_it_is_a_re_render(tmp_path, monkeypatch):
    """The re-render must be impossible to mistake for a measurement, and must not need the key -- a re-render
    that asked for `ARC_API_KEY` would be a re-render nobody could run without the ability to spend a sweep."""
    import sweep_chain
    res = _live_res()
    path = sweep_chain.dump_res(res, str(tmp_path / "res.json"))
    monkeypatch.delenv("ARC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["sweep_chain.py", "--render", path])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sweep_chain.main()
    out = buf.getvalue()
    assert "RE-RENDER of a BANKED sweep" in out, out
    assert "Nothing here contacted the API" in out.replace("\n", " ").replace("  ", " "), out
    assert sweep_chain.render_to_string(res) in out          # the body is the same render, not a summary of it


def test_the_sidecar_path_is_never_inside_the_repo_by_default(monkeypatch):
    """`res` carries a live scorecard id. The default destination is /tmp on purpose: a sidecar that defaulted
    into the working tree is a sidecar that eventually gets committed."""
    import sweep_chain
    monkeypatch.delenv("SWEEP_JSON", raising=False)
    p = sweep_chain.sidecar_path()
    assert p.startswith("/tmp/"), p
    monkeypatch.setenv("SWEEP_JSON", "/tmp/explicit.json")
    assert sweep_chain.sidecar_path() == "/tmp/explicit.json"
    assert os.path.basename(p).endswith(".json")
