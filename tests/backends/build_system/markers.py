import platform

import pytest


skip_if_windows = pytest.mark.skipif(platform.system() not in ['Darwin', 'Linux'],
                                     reason="This test does not run on windows.")
if_windows = pytest.mark.skipif(platform.system() in ['Darwin', 'Linux'],
                                     reason="This test only runs on windows.")
