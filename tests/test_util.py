"""Test utility functions."""

# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.util.util import always_str_list, str_if_possible


class TestAlwaysStrList:
    """Tests for always_str_list function."""

    @pytest.mark.parametrize(
        "name, input_data, expected",
        [
            ("single-string", "patch.txt", ["patch.txt"]),
            ("list-of-strings", ["patch1.txt", "patch2.txt"], ["patch1.txt", "patch2.txt"]),
            ("empty-string", "", []),
            ("empty-list", [], []),
            ("single-item-list", ["patch.txt"], ["patch.txt"]),
            ("multiple-item-list", ["a", "b", "c"], ["a", "b", "c"]),
            ("whitespace-string", "  spaces  ", ["  spaces  "]),
            ("special-chars-string", "patch-file_v1.0.txt", ["patch-file_v1.0.txt"]),
        ],
    )
    def test_always_str_list(self, name, input_data, expected):
        """Test always_str_list converts data correctly."""
        result = always_str_list(input_data)
        assert result == expected
        assert isinstance(result, list)

    def test_always_str_list_returns_same_list_object(self):
        """Test that passing a list returns the same list object."""
        input_list = ["a", "b"]
        result = always_str_list(input_list)
        assert result is input_list


class TestStrIfPossible:
    """Tests for str_if_possible function."""

    @pytest.mark.parametrize(
        "name, input_data, expected",
        [
            ("single-item", ["patch.txt"], "patch.txt"),
            ("multiple-items", ["patch1.txt", "patch2.txt"], ["patch1.txt", "patch2.txt"]),
            ("empty-list", [], ""),
            ("three-items", ["a", "b", "c"], ["a", "b", "c"]),
            ("single-empty-string", [""], ""),
            ("whitespace-single", ["  "], "  "),
            ("special-chars", ["patch-v1.0_final.txt"], "patch-v1.0_final.txt"),
        ],
    )
    def test_str_if_possible(self, name, input_data, expected):
        """Test str_if_possible converts data correctly."""
        result = str_if_possible(input_data)
        assert result == expected

    def test_str_if_possible_preserves_list_object(self):
        """Test that multi-item lists are returned unchanged."""
        input_list = ["a", "b", "c"]
        result = str_if_possible(input_list)
        assert result is input_list


class TestRoundTripConversion:
    """Test round-trip conversions between always_str_list and str_if_possible."""

    @pytest.mark.parametrize(
        "name, original",
        [
            ("single-string", "patch.txt"),
            ("empty-string", ""),
            ("list-single", ["patch.txt"]),
            ("list-multiple", ["a", "b"]),
            ("list-empty", []),
        ],
    )
    def test_roundtrip_always_to_str(self, name, original):
        """Test that always_str_list -> str_if_possible works correctly."""
        intermediate = always_str_list(original)
        result = str_if_possible(intermediate)

        # Check the result matches expected behavior
        if isinstance(original, str):
            if original:
                assert result == original
            else:
                assert result == ""
        elif len(original) == 0:
            assert result == ""
        elif len(original) == 1:
            assert result == original[0]
        else:
            assert result == original

    @pytest.mark.parametrize(
        "name, original",
        [
            ("empty-list", []),
            ("single-item", ["patch.txt"]),
            ("multiple-items", ["a", "b", "c"]),
        ],
    )
    def test_roundtrip_str_to_always(self, name, original):
        """Test that str_if_possible -> always_str_list works correctly."""
        intermediate = str_if_possible(original)
        result = always_str_list(intermediate)

        # Result should always be a list
        assert isinstance(result, list)
        if len(original) == 0:
            assert result == []
        elif len(original) == 1:
            assert result == original
        else:
            assert result == original


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_always_str_list_with_unicode(self):
        """Test handling of Unicode strings."""
        unicode_str = "patch_ñ_文字.txt"
        result = always_str_list(unicode_str)
        assert result == [unicode_str]

    def test_str_if_possible_with_unicode(self):
        """Test handling of Unicode in lists."""
        unicode_list = ["patch_ñ.txt"]
        result = str_if_possible(unicode_list)
        assert result == "patch_ñ.txt"

    def test_always_str_list_with_paths(self):
        """Test handling of path-like strings."""
        path = "path/to/patch.txt"
        result = always_str_list(path)
        assert result == [path]

    def test_str_if_possible_with_paths(self):
        """Test handling of path-like strings in lists."""
        paths = ["path/to/patch1.txt"]
        result = str_if_possible(paths)
        assert result == "path/to/patch1.txt"