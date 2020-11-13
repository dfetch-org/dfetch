"""Test the manifest."""
# mypy: ignore-errors


from unittest.mock import patch, mock_open

from dfetch.manifest.manifest import Manifest

BASIC_MANIFEST = u"""
manifest:
   version: 0

   remotes:
   - name: my-remote
     url-base: "http://www.myremote.com/"

   projects:
   - name: my-project
"""


def given_manifest_from_text(text: str) -> Manifest:
    """Given the manifest as specified."""
    with patch("dfetch.manifest.manifest.open", mock_open(read_data=text)):
        return Manifest.from_file("manifest.yaml")


def test_can_read_version() -> None:
    """Test that the version can be read."""
    manifest = given_manifest_from_text(BASIC_MANIFEST)
    assert manifest.version == 0
