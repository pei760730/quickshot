"""Tests for operator config behavior."""

import pytest

from lib.config import DEFAULT_OPERATOR, OPERATORS, current_operator, get_operator_paths, set_operator


class TestSetOperator:
    def test_default_operator_matches_config(self):
        assert current_operator() == DEFAULT_OPERATOR
        assert DEFAULT_OPERATOR in OPERATORS

    @pytest.mark.parametrize("op", list(OPERATORS.keys()))
    def test_set_operator_valid(self, op):
        set_operator(op)
        assert current_operator() == op

    def test_set_operator_invalid(self):
        with pytest.raises(ValueError, match="未知操作員"):
            set_operator("nonexistent")

    @pytest.mark.parametrize("op", list(OPERATORS.keys()))
    def test_get_operator_paths(self, op):
        paths = get_operator_paths(op)
        assert paths["vid_prefix"] == "VID"
        assert paths["idea_prefix"] == "IDEA"
        assert paths["operator"] == op

    def test_operators_config_complete(self):
        assert len(OPERATORS) > 0
        assert DEFAULT_OPERATOR in OPERATORS
        for _, cfg in OPERATORS.items():
            assert "data_dir" in cfg
            assert "production_subdir" in cfg
            assert "brain_path" in cfg
