import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# lex()
# ---------------------------------------------------------------------------

def test_lex_strips_tags():
    from layout import lex
    assert lex("<p>Hello</p>") == "Hello"

def test_lex_skips_script():
    from layout import lex
    assert "alert" not in lex("<script>alert(1)</script><p>Hi</p>")

def test_lex_skips_style():
    from layout import lex
    assert "color" not in lex("<style>body{color:red}</style><p>Hi</p>")

def test_lex_decodes_entities():
    from layout import lex
    assert "<" in lex("<p>&lt;div&gt;</p>")

def test_lex_preserves_newlines():
    from layout import lex
    result = lex("<p>line1</p>\n<p>line2</p>")
    assert "\n" in result

def test_lex_empty_body():
    from layout import lex
    assert lex("") == ""

def test_lex_no_tags():
    from layout import lex
    assert lex("plain text") == "plain text"


# ---------------------------------------------------------------------------
# layout()
# ---------------------------------------------------------------------------

def test_layout_empty_string():
    from layout import layout
    assert layout("") == []

def test_layout_returns_list_of_tuples():
    from layout import layout
    dl = layout("AB")
    assert len(dl) == 2
    x, y, c = dl[0]
    assert c == "A"
    assert isinstance(x, (int, float))
    assert isinstance(y, (int, float))

def test_layout_advances_x():
    from layout import layout, HSTEP
    dl = layout("AB")
    assert dl[1][0] == dl[0][0] + HSTEP

def test_layout_wraps_at_width():
    from layout import layout
    # 충분히 긴 문자열로 줄바꿈 강제
    dl = layout("A" * 100)
    ys = [y for _, y, _ in dl]
    assert max(ys) > min(ys)

def test_layout_newline_advances_y():
    from layout import layout, VSTEP
    dl = layout("A\nB")
    y_a = dl[0][1]
    y_b = next(y for _, y, c in dl if c == "B")
    assert y_b > y_a + VSTEP  # 단락 간격이 있으므로 VSTEP보다 커야 함

def test_layout_respects_custom_width():
    from layout import layout
    text = "A" * 30
    dl_wide = layout(text, width=800)
    dl_narrow = layout(text, width=200)
    max_y_wide = max(y for _, y, _ in dl_wide)
    max_y_narrow = max(y for _, y, _ in dl_narrow)
    assert max_y_narrow > max_y_wide
