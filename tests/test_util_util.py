import hashlib
import tempfile
import pytest

# Import the functions from the module where they are defined
from dfetch.util.util import  hash_file

@pytest.mark.parametrize("file_content, expected_hash", [
    (b"Test content", "8bfa8e0684108f419933a5995264d150"),
    (b"Another content", "0b583baba205856903798f53e48a77a1"),
    # Add more test cases as needed
])
def test_hash_file(file_content: bytes, expected_hash: str) -> None:

    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(file_content)
        temp_file.seek(0)

        digest = hashlib.md5()
        result_hash = hash_file(temp_file.name, digest).hexdigest()

    assert result_hash == expected_hash

