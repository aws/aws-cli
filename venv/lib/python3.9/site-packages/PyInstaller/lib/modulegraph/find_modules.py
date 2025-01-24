"""
modulegraph.find_modules - High-level module dependency finding interface
=========================================================================

History
........

Originally (loosely) based on code in py2exe's build_exe.py by Thomas Heller.
"""
import sys
import os
import pkgutil

from . import modulegraph
from .modulegraph import Alias

_PLATFORM_MODULES = {'posix', 'nt', 'os2', 'mac', 'ce', 'riscos'}


def get_implies():
    result = {
        # imports done from builtin modules in C code
        # (untrackable by modulegraph)
        "_curses":      ["curses"],
        "posix":        ["resource"],
        "gc":           ["time"],
        "time":         ["_strptime"],
        "datetime":     ["time"],
        "MacOS":        ["macresource"],
        "cPickle":      ["copy_reg", "cStringIO"],
        "parser":       ["copy_reg"],
        "codecs":       ["encodings"],
        "cStringIO":    ["copy_reg"],
        "_sre":         ["copy", "string", "sre"],
        "zipimport":    ["zlib"],

        # Python 3.2:
        "_datetime":    ["time", "_strptime"],
        "_json":        ["json.decoder"],
        "_pickle":      ["codecs", "copyreg", "_compat_pickle"],
        "_posixsubprocess": ["gc"],
        "_ssl":         ["socket"],

        # Python 3.3:
        "_elementtree": ["copy", "xml.etree.ElementPath"],

        # mactoolboxglue can do a bunch more of these
        # that are far harder to predict, these should be tracked
        # manually for now.

        # this isn't C, but it uses __import__
        "anydbm":       ["dbhash", "gdbm", "dbm", "dumbdbm", "whichdb"],
        # package aliases
        "wxPython.wx":  Alias('wx'),

    }

    if sys.version_info[0] == 3:
        result["_sre"] = ["copy", "re"]
        result["parser"] = ["copyreg"]

        # _frozen_importlib is part of the interpreter itself
        result["_frozen_importlib"] = None

    if sys.version_info[0] == 2 and sys.version_info[1] >= 5:
        result.update({
            "email.base64MIME":         Alias("email.base64mime"),
            "email.Charset":            Alias("email.charset"),
            "email.Encoders":           Alias("email.encoders"),
            "email.Errors":             Alias("email.errors"),
            "email.Feedparser":         Alias("email.feedParser"),
            "email.Generator":          Alias("email.generator"),
            "email.Header":             Alias("email.header"),
            "email.Iterators":          Alias("email.iterators"),
            "email.Message":            Alias("email.message"),
            "email.Parser":             Alias("email.parser"),
            "email.quopriMIME":         Alias("email.quoprimime"),
            "email.Utils":              Alias("email.utils"),
            "email.MIMEAudio":          Alias("email.mime.audio"),
            "email.MIMEBase":           Alias("email.mime.base"),
            "email.MIMEImage":          Alias("email.mime.image"),
            "email.MIMEMessage":        Alias("email.mime.message"),
            "email.MIMEMultipart":      Alias("email.mime.multipart"),
            "email.MIMENonMultipart":   Alias("email.mime.nonmultipart"),
            "email.MIMEText":           Alias("email.mime.text"),
        })

    if sys.version_info[:2] >= (2, 5):
        result["_elementtree"] = ["pyexpat"]

        import xml.etree
        for _, module_name, is_package in pkgutil.iter_modules(xml.etree.__path__):
            if not is_package:
                result["_elementtree"].append("xml.etree.%s" % (module_name,))

    if sys.version_info[:2] >= (2, 6):
        result['future_builtins'] = ['itertools']

    # os.path is an alias for a platform specific submodule,
    # ensure that the graph shows this.
    result['os.path'] = Alias(os.path.__name__)

    return result


def _replacePackages():
    REPLACEPACKAGES = {
        '_xmlplus':     'xml',
    }
    for k, v in REPLACEPACKAGES.items():
        modulegraph.replacePackage(k, v)


_replacePackages()
