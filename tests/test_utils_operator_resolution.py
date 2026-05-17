from pathlib import Path
import importlib.util


def _load_config_module():
    path = Path(__file__).resolve().parent.parent / "scripts" / "utils" / "lib" / "config.py"
    spec = importlib.util.spec_from_file_location("utils_config", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_resolve_operator_fallbacks_to_default():
    mod = _load_config_module()
    assert mod.resolve_operator(None) == mod.DEFAULT_OPERATOR
    assert mod.resolve_operator("") == mod.DEFAULT_OPERATOR
    assert mod.resolve_operator("unknown") == mod.DEFAULT_OPERATOR


def test_get_operator_tabs_uses_resolved_operator():
    mod = _load_config_module()
    tabs = mod.get_operator_tabs("unknown")
    assert tabs == mod.OPERATOR_SHEETS[mod.DEFAULT_OPERATOR]
