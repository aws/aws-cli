import sys

import pytest

from backends.build_system.validate_env import UnmetDependenciesException
from backends.build_system.utils import Requirement


@pytest.fixture
def unmet_error(request):
    error = UnmetDependenciesException([
        ('colorama', '1.0', Requirement('colorama', '>=2.0', '<3.0')),
    ], in_venv=request.param)
    return str(error)


class TestUnmetDependencies:
    @pytest.mark.parametrize('unmet_error', [False], indirect=True)
    def test_in_error_message(self, unmet_error):
        assert (
            "colorama (required: ('>=2.0', '<3.0')) (version installed: 1.0)"
        ) in unmet_error
        assert (
            f"{sys.executable} -m pip install --prefer-binary 'colorama>=2.0,<3.0'"
        ) in unmet_error

    @pytest.mark.parametrize('unmet_error', [False], indirect=True)
    def test_not_in_venv(self, unmet_error):
        assert 'We noticed you are not in a virtualenv.' in unmet_error

    @pytest.mark.parametrize('unmet_error', [True], indirect=True)
    def test_in_venv(self, unmet_error):
        assert 'We noticed you are not in a virtualenv.' not in unmet_error
