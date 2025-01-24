# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""The version and URL for coverage.py"""
# This file is exec'ed in setup.py, don't import anything!

# version_info: same semantics as sys.version_info.
# _dev: the .devN suffix if any.
version_info = (7, 0, 1, "final", 0)
_dev = 0


def _make_version(major, minor, micro, releaselevel="final", serial=0, dev=0):
    """Create a readable version string from version_info tuple components."""
    assert releaselevel in ['alpha', 'beta', 'candidate', 'final']
    version = "%d.%d.%d" % (major, minor, micro)
    if releaselevel != 'final':
        short = {'alpha': 'a', 'beta': 'b', 'candidate': 'rc'}[releaselevel]
        version += f"{short}{serial}"
    if dev != 0:
        version += f".dev{dev}"
    return version


def _make_url(major, minor, micro, releaselevel, serial=0, dev=0):
    """Make the URL people should start at for this version of coverage.py."""
    url = "https://coverage.readthedocs.io"
    if releaselevel != "final" or dev != 0:
        # For pre-releases, use a version-specific URL.
        url += "/en/" + _make_version(major, minor, micro, releaselevel, serial, dev)
    return url


__version__ = _make_version(*version_info, _dev)
__url__ = _make_url(*version_info, _dev)
