import sys

if sys.version_info[0] == 2:
    PY2 = True

    from StringIO import StringIO
    BytesIO = StringIO
    from urllib import pathname2url
    _cOrd = ord

    # File open mode for reading (univeral newlines)
    _READ_MODE = "rU"

else:
    PY2 = False

    from urllib.request import pathname2url
    from io import BytesIO, StringIO
    _cOrd = int
    _READ_MODE = "r"

if sys.version_info < (3,):
    from dis3 import get_instructions
else:
    from dis import get_instructions
