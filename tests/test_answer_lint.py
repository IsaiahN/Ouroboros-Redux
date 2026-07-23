"""
The ANSWER-ENCODING tripwire. This is not a normal unit test -- it is the mechanical ground-maintainer for build
honesty (Tether §1.5). `test_real_agent_modules_are_game_agnostic` runs EVERY beat: if the LLM building this agent
ever special-cases a game (a game-id literal, or behaviour branching on game_id) the suite goes RED and it shows up
in the git diff a human reads on return. The positive tests prove the guard actually bites.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.answer_lint import lint_source, lint_agent_dir


def test_clean_source_passes():
    src = """
def choose(grid, game_id):
    # general logic keyed on nothing game-specific
    prefix = game_id.split('-')[0]     # keying a transfer table by identity is fine
    return bfs(grid)
"""
    assert lint_source(src) == []


def test_detects_full_game_id_literal():
    src = 'DEFAULT = "m0r0-492f87ba"\n'
    f = lint_source(src)
    assert any("full game-id literal" in r for _, r in f)


def test_detects_game_code_literal_used_in_logic():
    src = 'def act(g):\n    if colour_name == "s5i5":\n        return 6\n'
    f = lint_source(src)
    assert any("game-code" in r and "s5i5" in r for _, r in f)


def test_detects_behaviour_branching_on_game_id():
    src = 'def act(self, g):\n    if self.game_id == "x":\n        return special()\n    return general()\n'
    f = lint_source(src)
    assert any("branches on game_id" in r for _, r in f)


def test_docstrings_and_comments_are_exempt():
    # documentation may name games (it does not affect behaviour); only executable encoding is a violation
    src = '"""This organ wins m0r0 L1 and unlocks sc25."""\n' \
          "def act(g):\n    # g50t leaves a trail; tr87 is paint\n    return general(g)\n"
    assert lint_source(src) == []


def test_real_agent_modules_are_game_agnostic():
    # THE TRIPWIRE. If this fails, an agent-logic module encoded a specific game -> the generalisation claim broke.
    d = os.path.join(os.path.dirname(__file__), "..", "src", "newhorse", "redux_arch")
    problems = lint_agent_dir(d)
    assert problems == [], "answer-encoding detected in agent code:\n" + "\n".join(
        "  %s:%d  %s" % p for p in problems)
