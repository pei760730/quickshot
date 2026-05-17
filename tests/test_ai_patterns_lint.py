from scripts.lint.ai_patterns_lint import lint_text


def test_ai_pattern_rules_positive_and_negative():
    text = """
這段有很多—破折號—而且—超過三個。

**a**
**b**
**c**
- 🚀 start
Of course! this is fine
as of January 2026
The future looks bright.
"""
    findings = lint_text(text)
    ids = {f[0] for f in findings}
    assert {13, 14, 17, 19, 20, 24}.issubset(ids)

    clean = lint_text("正常文本\n- item\n無 AI 口癖")
    assert clean == []
