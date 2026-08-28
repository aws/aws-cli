import importlib.util
import sys
from pathlib import Path
from unittest import mock


def load_setup_module(argv=None):
    setup_path = Path(__file__).parents[2] / "setup.py"
    spec = importlib.util.spec_from_file_location(
        "awscli_setup",
        setup_path,
    )
    module = importlib.util.module_from_spec(spec)

    if argv is None:
        argv = ["setup.py"]

    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(sys.modules, {"py2exe": mock.Mock()}),
        mock.patch("setuptools.setup"),
    ):
        spec.loader.exec_module(module)

    return module


class TestFindVersion:
    def test_finds_version_without_spaces_around_equals(self):
        setup_module = load_setup_module()

        with mock.patch.object(
            setup_module,
            "read",
            return_value="__version__='1.2.3'",
        ):
            assert setup_module.find_version(
                "awscli",
                "__init__.py",
            ) == "1.2.3"

    def test_finds_version_with_multiple_spaces_around_equals(self):
        setup_module = load_setup_module()

        with mock.patch.object(
            setup_module,
            "read",
            return_value="__version__  =  '1.2.3'",
        ):
            assert setup_module.find_version(
                "awscli",
                "__init__.py",
            ) == "1.2.3"


class TestPy2ExeOptions:
    def test_uses_python3_package_names(self):
        setup_module = load_setup_module(["setup.py", "py2exe"])

        packages = setup_module.setup_options["options"]["py2exe"]["packages"]

        assert "http.client" in packages
        assert "html.parser" in packages
        assert "configparser" in packages

        assert "httplib" not in packages
        assert "HTMLParser" not in packages
        assert "ConfigParser" not in packages