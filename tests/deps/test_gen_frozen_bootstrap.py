import marshal
import re
import subprocess
import sys
from pathlib import Path


def test_frozen_bootstrap_is_independent_of_install_prefix(
    tmp_path: Path,
) -> None:
    generator = (
        Path(__file__).resolve().parents[2]
        / "deps/scripts/gen_frozen_bootstrap.py"
    )
    modules = (
        "encodings/__init__.py",
        "encodings/aliases.py",
        "encodings/utf_8.py",
        "encodings/latin_1.py",
        "encodings/ascii.py",
        "encodings/_win_cp_codecs.py",
        "importlib/__init__.py",
    )
    outputs: list[bytes] = []
    for location in ("install-a", "other tree/install-b"):
        prefix = tmp_path / location
        stdlib = prefix / "lib/python3.14"
        for module in ("os.py", *modules):
            path = stdlib / module
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("def bootstrap():\n    return 'fixture'\n")
        output = prefix / "bootstrap.c"
        subprocess.run(
            [sys.executable, str(generator), str(prefix), str(output)],
            check=True,
            capture_output=True,
        )
        outputs.append(output.read_bytes())
    assert outputs[0] == outputs[1]
    arrays = re.findall(
        rb"static const unsigned char \w+\[\] = \{(.*?)\};",
        outputs[0],
        re.DOTALL,
    )
    filenames = {
        marshal.loads(
            bytes(int(value, 16) for value in re.findall(rb"0x(..)", array))
        ).co_filename
        for array in arrays
    }
    expected = set(modules)
    if sys.platform != "win32":
        expected.remove("encodings/_win_cp_codecs.py")
    assert filenames == expected
