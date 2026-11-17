import builtins as _builtins
import io as _io
import sys
import os
import importlib as _importlib
import types as _types
import _zippy_finder

_ZIPPY_SENTINEL = "__ZIPPY__/"
_ZIPPY_BOTOCORE_DATA = "__ZIPPY__/awscli/botocore/data"
_ZIPPY_AWSCLI_DATA = "__ZIPPY__/awscli/data"
_SYNTHETIC_ROOT = "/<zippy>/"


def _sentinel_for_synthetic(path: str) -> "str | None":
    """The sentinel path for a path derived from a synthetic module filename.

    The synthetic filenames lay modules out as an installed package would, so
    a derived path names the payload entry at the same place. Windows makes
    the root drive-absolute with backslashes, so compare the drive-less,
    slash-separated form. None for any other path.
    """
    _, tail = os.path.splitdrive(os.path.normpath(path))
    tail = tail.replace(os.sep, "/")
    if not tail.startswith(_SYNTHETIC_ROOT):
        return None
    return _ZIPPY_SENTINEL + tail[len(_SYNTHETIC_ROOT):]


def _v2k(virtual_path):
    """Strip our virtual-path sentinel to recover the blob key.

    Payload keys always use forward slashes. botocore composes model paths
    with os.path.join, so on Windows a virtual path reaches us with the
    native separator in it. Normalizing before the sentinel is stripped also
    recognizes a path whose sentinel was itself joined natively; every caller
    passes a virtual path, never a real filesystem one, so a backslash in one
    is always a separator.
    """
    if os.sep != "/":
        virtual_path = virtual_path.replace(os.sep, "/")
    if virtual_path.startswith(_ZIPPY_SENTINEL):
        return virtual_path[len(_ZIPPY_SENTINEL):]
    return virtual_path


def _list_blob_dir(virtual_path):
    """Immediate children of a virtual directory path."""
    rel = _v2k(virtual_path).rstrip("/")
    blob_prefix = (rel + "/") if rel else ""
    return _zippy_finder.list_dir(blob_prefix)


def _list_blob_services(virtual_path, type_name):
    """Service names with a model file under a virtual data path."""
    rel = _v2k(virtual_path).rstrip("/")
    blob_prefix = (rel + "/") if rel else ""
    return _zippy_finder.list_services(blob_prefix, type_name)


def _list_blob_api_versions(virtual_path, service_name, type_name):
    """API versions with a model file for one service."""
    rel = _v2k(virtual_path).rstrip("/")
    blob_prefix = (rel + "/") if rel else ""
    return _zippy_finder.list_api_versions(blob_prefix, service_name, type_name)


def _read_blob_file(virtual_path):
    """Bytes for a virtual file path. None if missing."""
    try:
        return _zippy_finder.get_data(_v2k(virtual_path))
    except FileNotFoundError:
        return None


def _blob_isdir(virtual_path):
    rel = _v2k(virtual_path).rstrip("/")
    blob_prefix = (rel + "/") if rel else ""
    return _zippy_finder.has_prefix(blob_prefix)


def _blob_isfile(virtual_path):
    """Cheap existence check via the native hash lookup. Doesn't read the
    payload — important for compressed entries (examples, awscli/data) which
    list_available_services iterates over."""
    return _zippy_finder.exists(_v2k(virtual_path))


# ---- Wait for awscrt to finish shutting down ----
# awscrt shuts a released resource down on its own threads, and each step ends
# in a callback that takes the GIL. A released S3 client's callback runs on an
# event loop thread and releases the client's bootstrap, the bootstrap's
# callback releases its event loop group, and the group's cleanup thread then
# calls back the same way. awscrt skips a callback once Py_IsFinalizing() is
# true, but it checks before it takes the GIL: a callback that starts just as
# finalization begins gets a thread state that PyInterpreterState_Delete()
# frees under it, and the process crashes at exit. So the last exit handler
# waits for every S3 client, bootstrap and event loop group that has been
# released to finish shutting down.
#
# No other thread can find a callback's shutdown_event gone while the callback
# still holds anything else: the S3 client's drops the event and its other
# references together, in C, and the others drop the event last. So a released
# resource is done once its event is gone. is_set() is not enough: an S3
# client sets its event before it releases its bootstrap. The handler holds
# the events weakly; one that something else keeps alive holds exit up to the
# timeout. Other code that puts a weakref callback on an S3 client's event
# breaks this: the callback runs Python after the client's callback drops the
# event but before it releases the bootstrap, so the handler can return first.
#
# A resource still referenced when the handler returns is released during
# finalization, after Py_IsFinalizing() turns true, so awscrt skips its
# callbacks. The exception is a reference the atexit registry itself holds,
# such as an argument to another exit handler, which it drops before then.
import atexit as _atexit

_CRT_SHUTDOWN_TIMEOUT_SECONDS = 5.0
_crt_shutdowns = []


def _track_crt_shutdown(crt_class):
    import weakref

    init = crt_class.__init__

    def tracked_init(self, *args, **kwargs):
        init(self, *args, **kwargs)
        _crt_shutdowns.append(
            (weakref.ref(self), weakref.ref(self.shutdown_event))
        )

    crt_class.__init__ = tracked_init


def _wait_for_crt_shutdown():
    if not _crt_shutdowns:
        return
    import gc
    import time

    deadline = time.monotonic() + _CRT_SHUTDOWN_TIMEOUT_SECONDS
    # How many resources the previous pass found released, or None after a
    # wait, so that a pass that follows a wait is always checked again.
    released_before = 0
    try:
        while True:
            gc.collect()
            released = [
                event_ref
                for resource_ref, event_ref in _crt_shutdowns
                if resource_ref() is None
            ]
            pending = None
            for event_ref in released:
                pending = event_ref()
                if pending is not None:
                    break
            # A callback's own releases can start another resource's shutdown,
            # so finish only once a pass also finds nothing newly released.
            if pending is None and len(released) == released_before:
                return
            released_before = len(released)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            if pending is None:
                continue
            if pending.is_set():
                time.sleep(min(remaining, 0.001))
            else:
                pending.wait(remaining)
            del pending
            released_before = None
    except KeyboardInterrupt:
        return


# Exit handlers run in reverse order of registration, so registering this
# before anything else is imported puts it after every other exit handler,
# logging's included. threading's own shutdown, which joins non-daemon threads
# and concurrent.futures workers, runs before any exit handler.
_atexit.register(_wait_for_crt_shutdown)


_ZIPPY_CACERT_PATH = "<zippy:cacert>"
_cacert_pem_bytes = _zippy_finder.get_data("awscli/botocore/cacert.pem")
_cacert_bytes = _cacert_pem_bytes.decode("ascii")

import ssl as _ssl_mod
_orig_load_verify = _ssl_mod.SSLContext.load_verify_locations


def _patched_load_verify(self, cafile=None, capath=None, cadata=None):
    if cafile == _ZIPPY_CACERT_PATH:
        return _orig_load_verify(self, cadata=_cacert_bytes)
    return _orig_load_verify(self, cafile=cafile, capath=capath, cadata=cadata)


_ssl_mod.SSLContext.load_verify_locations = _patched_load_verify


# ---- Wire AWS CLI's TopLevelImportAliasFinder around our finder ----
# AWS CLI vendors botocore at awscli/botocore/. Its TopLevelImportAliasFinder
# (in awscli/__init__.py) translates `import botocore` → load from
# awscli/botocore/__init__.py — IF it can wrap an underlying finder whose
# class name is in its _TARGET_FINDERS list (defaults: PyInstaller's
# PyiFrozenImporter + native PathFinder).
#
# Importing awscli runs its __init__.py which calls add_alias_finder ONCE.
# At that point neither default target is suitable for us, so the wrap is
# useless — it routes `import botocore` through PathFinder (which can't see
# our blob). After import, we replace _TARGET_FINDERS with our class name,
# strip the dud wrapper, and re-run add_alias_finder.
import awscli
sys.meta_path[:] = [
    f for f in sys.meta_path
    if not isinstance(f, awscli.TopLevelImportAliasFinder)
]
awscli.TopLevelImportAliasFinder._TARGET_FINDERS = ["_zippy_finder.Finder"]
awscli.TopLevelImportAliasFinder.add_alias_finder(sys.meta_path)


# ---- Embedded CA bundle as botocore's default ----
# botocore resolves a client's CA bundle as --ca-bundle, then the ca_bundle
# chain (AWS_CA_BUNDLE, then the profile's ca_bundle), then
# REQUESTS_CA_BUNDLE, then its own DEFAULT_CA_BUNDLE (endpoint.py
# _get_verify_value, httpsession.get_cert_path). Making the sentinel that
# last default, rather than a value anywhere in the chain, keeps every
# setting in upstream's order and leaves a blank one to
# botocore's own error. httpsession.where() reads the global when it is
# called; customizations/s3/factory.py copies it when it is imported, which
# happens only after this runs. The alias finder loads
# awscli.botocore.httpsession, which awscli/customizations/sso/resolve.py
# imports get_cert_path from, as a second module object from the same file,
# with its own global; it is patched when it is imported, below.
import botocore.httpsession as _httpsession


def _install_default_ca_bundle(httpsession_module):
    httpsession_module.DEFAULT_CA_BUNDLE = _ZIPPY_CACERT_PATH


_install_default_ca_bundle(_httpsession)


_post_import_hooks = {}


class _HookedLoader:
    def __init__(self, loader, hook):
        self._loader = loader
        self._hook = hook

    def create_module(self, spec):
        return self._loader.create_module(spec)

    def exec_module(self, module):
        self._loader.exec_module(module)
        self._hook(module)


class _PostImportFinder:
    def find_spec(self, fullname, path=None, target=None):
        hook = _post_import_hooks.get(fullname)
        if hook is None:
            return None
        for finder in sys.meta_path:
            if finder is self:
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                break
        else:
            return None
        del _post_import_hooks[fullname]
        spec.loader = _HookedLoader(spec.loader, hook)
        return spec


sys.meta_path.insert(0, _PostImportFinder())


# The load_verify_locations patch above only covers TLS built through Python's
# ssl module. The CRT S3 client hands its `verify` value to
# awscrt.io.TlsContextOptions.override_default_trust_store_from_path, which
# reads the file in Python (awscrt/io.py) before native code ever sees it.
# Route the sentinel to awscrt's in-memory trust-store API so the embedded PEM
# is used without touching disk. Real user-supplied paths pass through.
def _patch_awscrt_tls(io_module):
    _orig_override = (
        io_module.TlsContextOptions.override_default_trust_store_from_path
    )

    def _patched_override(self, ca_dirpath=None, ca_filepath=None):
        if ca_filepath == _ZIPPY_CACERT_PATH:
            return self.override_default_trust_store(_cacert_pem_bytes)
        return _orig_override(
            self, ca_dirpath=ca_dirpath, ca_filepath=ca_filepath
        )

    io_module.TlsContextOptions.override_default_trust_store_from_path = (
        _patched_override
    )


def _patch_awscrt_io(io_module):
    _patch_awscrt_tls(io_module)
    _track_crt_shutdown(io_module.EventLoopGroup)
    _track_crt_shutdown(io_module.ClientBootstrap)


def _patch_awscrt_s3(s3_module):
    _track_crt_shutdown(s3_module.S3Client)


_post_import_hooks["awscrt.io"] = _patch_awscrt_io
_post_import_hooks["awscrt.s3"] = _patch_awscrt_s3

_AWSCLI_HTTPSESSION = "awscli.botocore.httpsession"
if _AWSCLI_HTTPSESSION in sys.modules:
    _install_default_ca_bundle(sys.modules[_AWSCLI_HTTPSESSION])
else:
    _post_import_hooks[_AWSCLI_HTTPSESSION] = _install_default_ca_bundle


_AUTOCOMPLETE_INDEX_DIR = "awscli/autocomplete/index/"
_AUTOCOMPLETE_INDEX_ROOT = "_root"


def _autocomplete_index_entry(parent: str) -> str:
    """The payload key of the entry holding the rows whose parent is `parent`.

    Mirrors entry_name in deps/scripts/gen_ac_index.py.
    """
    lineage = parent.split(".")
    name = lineage[1] if len(lineage) > 1 else _AUTOCOMPLETE_INDEX_ROOT
    return f"{_AUTOCOMPLETE_INDEX_DIR}{name}.json"


def _insert_autocomplete_index_rows(
    database: "sqlite3.Connection", entry: dict
) -> None:
    """Insert an entry's rows. Mirrors load_entry in gen_ac_index.py."""
    database.executemany(
        "INSERT INTO command_table (command, full_name, parent) "
        "VALUES (?, ?, ?)",
        [
            (command, full_name, parent)
            for parent, rows in entry["commands"].items()
            for command, full_name in rows
        ],
    )
    database.executemany(
        "INSERT INTO param_table (param_id, command, parent, argname, "
        "type_name, nargs, positional_arg, required) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (first_param_id + offset, command, parent, *row)
            for parent, commands in entry["params"].items()
            for command, (first_param_id, rows) in commands.items()
            for offset, row in enumerate(rows)
        ],
    )
    database.executemany(
        "INSERT INTO apicall_table (param_id, apicall_data) VALUES (?, ?)",
        entry["apicalls"],
    )


class _PayloadIndexConnection:
    """The payload's autocomplete index, loaded one entry at a time.

    Auto-prompt computes completions on worker threads. Like upstream's, the
    connection is shared across them, and a lock keeps two threads from
    loading the same entry twice.
    """

    def __init__(self) -> None:
        import threading

        self._lock = threading.Lock()
        self._database: "sqlite3.Connection | None" = None
        self._loaded: "set[str]" = set()

    def execute(self, query: str, **kwargs: object) -> "sqlite3.Cursor":
        with self._lock:
            database = self._open()
            parent = kwargs.get("parent")
            if isinstance(parent, str):
                self._load(database, _autocomplete_index_entry(parent))
            else:
                for name in _zippy_finder.list_dir(_AUTOCOMPLETE_INDEX_DIR):
                    self._load(database, _AUTOCOMPLETE_INDEX_DIR + name)
        return database.execute(query, kwargs)

    def close(self) -> None:
        if self._database is not None:
            self._database.close()

    def _open(self) -> "sqlite3.Connection":
        if self._database is None:
            import json
            import sqlite3

            key = _autocomplete_index_entry("")
            root = json.loads(_zippy_finder.get_data(key))
            database = sqlite3.connect(
                ":memory:", check_same_thread=False, isolation_level=None
            )
            for statement in root["schema"]:
                database.execute(statement)
            _insert_autocomplete_index_rows(database, root)
            self._loaded.add(key)
            self._database = database
        return self._database

    def _load(self, database: "sqlite3.Connection", key: str) -> None:
        if key in self._loaded:
            return
        try:
            data = _zippy_finder.get_data(key)
        except FileNotFoundError:
            self._loaded.add(key)
            return
        import json

        entry = json.loads(data)
        self._loaded.add(key)
        _insert_autocomplete_index_rows(database, entry)


def _patch_autocomplete_db(db_module: _types.ModuleType) -> None:
    file_connection = db_module.DatabaseConnection

    def _connect(db_filename: "str | None" = None) -> object:
        if (
            db_filename is None
            and not os.path.isfile(db_module.INDEX_FILE)
            and _zippy_finder.exists(_autocomplete_index_entry(""))
        ):
            return _PayloadIndexConnection()
        return file_connection(db_filename)

    db_module.DatabaseConnection = _connect


_post_import_hooks["awscli.autocomplete.db"] = _patch_autocomplete_db


# ---- SSO login callback page ----
# The authorization code flow's callback handler (OAuthCallbackHandler.do_GET
# in awscli/customizations/sso/utils.py) serves the sign-in page from
# os.path.join(os.path.dirname(__file__), 'index.html'). Our synthetic
# __file__ has no directory, so that path is a bare 'index.html' relative to
# the working directory: the open raises after the 200 headers go out and
# before the auth code is read, and login waits out its ten-minute timeout,
# or it serves whatever index.html the working directory holds. The module
# reads nothing else with open, so it gets one that serves the page's path
# from the payload, whatever is on disk.
_SSO_CALLBACK_PAGE = "awscli/customizations/sso/index.html"


def _serve_sso_callback_page(utils_module: _types.ModuleType) -> None:
    page_path = os.path.join(
        os.path.dirname(utils_module.__file__), "index.html"
    )

    def _open_callback_page(file, mode="r", *args, **kwargs):
        if file == page_path and mode == "rb":
            return _io.BytesIO(_zippy_finder.get_data(_SSO_CALLBACK_PAGE))
        return _builtins.open(file, mode, *args, **kwargs)

    utils_module.open = _open_callback_page


_post_import_hooks["awscli.customizations.sso.utils"] = (
    _serve_sso_callback_page
)


def _replace_plugin_entry(registry, old_entry, new_entry):
    for event_name, entries in registry.items():
        registry[event_name] = [
            new_entry if entry == old_entry else entry
            for entry in entries
        ]


import awscli.handlers_registry as _handlers_registry

_ZIPPY_HOOKS_MODULE = "_zippy_runtime_hooks"
_replace_plugin_entry(
    _handlers_registry.PLUGIN_REGISTRY,
    ("awscli.customizations.waiters", "register_add_waiters"),
    (_ZIPPY_HOOKS_MODULE, "register_add_waiters"),
)
_replace_plugin_entry(
    _handlers_registry.PLUGIN_REGISTRY,
    ("awscli.customizations.wizard.commands", "register_wizard_commands"),
    (_ZIPPY_HOOKS_MODULE, "register_wizard_commands"),
)
_replace_plugin_entry(
    _handlers_registry.PLUGIN_REGISTRY,
    ("awscli.customizations.addexamples", "register_docs_add_examples"),
    (_ZIPPY_HOOKS_MODULE, "register_docs_add_examples"),
)


_help_stub = _types.ModuleType("awscli.help")
_real_help_module = None


def _load_real_help_class(class_name):
    global _real_help_module
    if _real_help_module is None:
        if sys.modules.get("awscli.help") is _help_stub:
            del sys.modules["awscli.help"]
        _real_help_module = _importlib.import_module("awscli.help")
        _patch_help_modules()
    return getattr(_real_help_module, class_name)


class _LazyHelpCommand:
    _real_class_name = ""

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._real = None

    def _resolve(self):
        if self._real is None:
            cls = _load_real_help_class(self._real_class_name)
            self._real = cls(*self._args, **self._kwargs)
            object.__setattr__(self, "_args", ())
            object.__setattr__(self, "_kwargs", {})
        return self._real

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._resolve(), name)

    def __setattr__(self, name, value):
        # The wrapper's own bookkeeping (set in __init__/_resolve) must land on
        # the wrapper itself; anything else (e.g. autoprompt's
        # `help_command.renderer = FileRenderer()`) must reach the resolved real
        # command so the real __call__ renders through the caller's renderer/doc.
        if name in ("_args", "_kwargs", "_real"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._resolve(), name, value)


class HelpCommand:
    EventHandlerClass = None

    def __init__(self, session, obj, command_table, arg_table):
        self.session = session
        self.obj = obj
        self.command_table = command_table or {}
        self.arg_table = arg_table or {}
        self._subcommand_table = {}
        self._related_items = []
        self._base_remote_url = getattr(awscli, "_DEFAULT_BASE_REMOTE_URL", "")
        try:
            self._help_output_format = self.session.get_config_variable(
                "cli_help_output"
            )
        except Exception:
            self._help_output_format = None

    @property
    def subcommand_table(self):
        return self._subcommand_table

    @property
    def related_items(self):
        return self._related_items

    # `doc` and `renderer` mirror upstream's __init__ attributes, but lazily.
    # Upstream creates both in __init__; here we defer so bootstrap never imports
    # the help machinery. First materialization also loads the real help module,
    # which runs _patch_help_modules() so example/doc patching is in place
    # before events fire (this is the trigger on the BasicHelp path, whose own
    # __call__ never calls _load_real_help_class).
    @property
    def doc(self):
        if "doc" not in self.__dict__:
            from awscli.bcdoc.restdoc import ReSTDocument

            _load_real_help_class("HelpCommand")
            self.__dict__["doc"] = ReSTDocument(target="man")
        return self.__dict__["doc"]

    @doc.setter
    def doc(self, value):
        self.__dict__["doc"] = value

    @property
    def renderer(self):
        if "renderer" not in self.__dict__:
            get_renderer = _load_real_help_class("get_renderer")
            self.__dict__["renderer"] = get_renderer(self._help_output_format)
        return self.__dict__["renderer"]

    @renderer.setter
    def renderer(self, value):
        self.__dict__["renderer"] = value

    def __call__(self, args, parsed_globals):
        from awscli.argparser import ArgTableArgParser
        from awscli.bcdoc import docevents

        if args:
            subcommand_parser = ArgTableArgParser({}, self.subcommand_table)
            parsed, remaining = subcommand_parser.parse_known_args(args)
            if getattr(parsed, "subcommand", None) is not None:
                return self.subcommand_table[parsed.subcommand](
                    remaining, parsed_globals
                )

        instance = self.EventHandlerClass(self)
        docevents.generate_events(self.session, self)
        if self._help_output_format == "url":
            self.renderer.render(self.url.encode())
        else:
            self.renderer.render(self.doc.getvalue())
        instance.unregister()


class ProviderHelpCommand(_LazyHelpCommand):
    _real_class_name = "ProviderHelpCommand"


class ServiceHelpCommand(_LazyHelpCommand):
    _real_class_name = "ServiceHelpCommand"


class OperationHelpCommand(_LazyHelpCommand):
    _real_class_name = "OperationHelpCommand"


_help_stub.HelpCommand = HelpCommand
_help_stub.ProviderHelpCommand = ProviderHelpCommand
_help_stub.ServiceHelpCommand = ServiceHelpCommand
_help_stub.OperationHelpCommand = OperationHelpCommand
sys.modules["awscli.help"] = _help_stub


import botocore.loaders as _loaders


_orig_jfl_exists = _loaders.JSONFileLoader.exists
_orig_jfl_load = _loaders.JSONFileLoader.load_file


def _patched_exists(self, file_path):
    if file_path.startswith("__ZIPPY__/"):
        return _blob_isfile(file_path + ".json")
    return _orig_jfl_exists(self, file_path)


def _patched_load_file(self, file_path):
    if file_path.startswith("__ZIPPY__/"):
        data = _read_blob_file(file_path + ".json")
        if data is None:
            return None
        from awscli.botocore.compat import OrderedDict, json
        return json.loads(data.decode("utf-8"), object_pairs_hook=OrderedDict)
    return _orig_jfl_load(self, file_path)


_loaders.JSONFileLoader.exists = _patched_exists
_loaders.JSONFileLoader.load_file = _patched_load_file


# Override Loader's directory-traversal helpers to handle __ZIPPY__/ search
# paths alongside disk paths. The original instance_cache decorator (in
# botocore/loaders.py) doesn't preserve __wrapped__, so we define replacements
# that handle both blob paths and real disk paths.
def _patched_potential_locations(self, name=None, must_exist=False, is_dir=False):
    for path in self.search_paths:
        if path.startswith("__ZIPPY__/"):
            full_path = path
            if name is not None:
                full_path = path.rstrip("/") + "/" + name
            if not must_exist:
                yield full_path
            elif is_dir and _blob_isdir(full_path):
                yield full_path
            elif (not is_dir) and (_blob_isfile(full_path) or _blob_isdir(full_path)):
                yield full_path
        elif os.path.isdir(path):
            full_path = path
            if name is not None:
                full_path = os.path.join(path, name)
            if not must_exist:
                yield full_path
            elif is_dir and os.path.isdir(full_path):
                yield full_path
            elif os.path.exists(full_path):
                yield full_path


def _patched_list_available_services(self, type_name):
    zippy_results = []
    disk_services = set()
    saw_disk_path = False
    for path in self.search_paths:
        if path.startswith("__ZIPPY__/"):
            services = _list_blob_services(path, type_name)
            if services:
                zippy_results.append(services)
        elif os.path.isdir(path):
            saw_disk_path = True
            for d in os.listdir(path):
                if not os.path.isdir(os.path.join(path, d)):
                    continue
                for v in os.listdir(os.path.join(path, d)):
                    if os.path.isfile(os.path.join(path, d, v, type_name + ".json")):
                        disk_services.add(d)
                        break
    if not saw_disk_path and len(zippy_results) == 1:
        return sorted(zippy_results[0])
    services = set(disk_services)
    for result in zippy_results:
        services.update(result)
    return sorted(services)


def _patched_list_api_versions(self, service_name, type_name):
    zippy_results = []
    disk_versions = set()
    saw_disk_path = False
    for path in self.search_paths:
        if path.startswith("__ZIPPY__/"):
            versions = _list_blob_api_versions(path, service_name, type_name)
            if versions:
                zippy_results.append(versions)
        # Upstream's _potential_locations skips a search path that is not a
        # directory. An empty AWS_DATA_PATH entry is not one, but joined with
        # the service name it would name a directory in the working directory.
        elif os.path.isdir(path) and os.path.isdir(os.path.join(path, service_name)):
            saw_disk_path = True
            for v in os.listdir(os.path.join(path, service_name)):
                if os.path.isfile(os.path.join(path, service_name, v, type_name + ".json")):
                    disk_versions.add(v)
    if not saw_disk_path and len(zippy_results) == 1:
        return zippy_results[0]
    known = set(disk_versions)
    for result in zippy_results:
        known.update(result)
    if not known:
        from awscli.botocore.exceptions import DataNotFoundError
        raise DataNotFoundError(data_path=service_name)
    return sorted(known)


_loaders.Loader._potential_locations = _patched_potential_locations
_loaders.Loader.list_available_services = _loaders.instance_cache(
    _patched_list_available_services
)
_loaders.Loader.list_api_versions = _loaders.instance_cache(
    _patched_list_api_versions
)
_loaders.Loader.BUILTIN_DATA_PATH = "__ZIPPY__/awscli/botocore/data"


# Patch Loader.__init__ to replace each search path derived from a synthetic
# module filename with its sentinel, in place, and to append the sentinels
# when missing. awscli/__init__.py appends the data directory beside its own
# __file__, /<zippy>/awscli/data, to AWS_DATA_PATH, so that entry becomes
# __ZIPPY__/awscli/data at upstream's position: after the user's paths,
# before ~/.aws/models. Where a path came from decides, never whether it
# exists: user paths stay as given, as upstream keeps them, and the variable
# a child process inherits names nothing in its working directory.
_orig_loader_init = _loaders.Loader.__init__


def _patched_loader_init(self, *a, **kw):
    _orig_loader_init(self, *a, **kw)
    search_paths = []
    for path in self._search_paths:
        path = _sentinel_for_synthetic(path) or path
        if path not in search_paths:
            search_paths.append(path)
    for sp in (_ZIPPY_AWSCLI_DATA, _ZIPPY_BOTOCORE_DATA):
        if sp not in search_paths:
            search_paths.append(sp)
    self._search_paths = search_paths


_loaders.Loader.__init__ = _patched_loader_init


_zippy_distribution_type = None


def _normalize_distribution_name(name):
    normalized = []
    separator_pending = False
    for char in name.lower():
        if char in "-_.":
            separator_pending = bool(normalized)
            continue
        if separator_pending:
            normalized.append("-")
            separator_pending = False
        normalized.append(char)
    return "".join(normalized)


def _get_zippy_distribution_type():
    global _zippy_distribution_type
    if _zippy_distribution_type is not None:
        return _zippy_distribution_type

    from importlib.metadata import Distribution

    class ZippyDistribution(Distribution):
        def __init__(self, metadata_dir):
            self._metadata_dir = metadata_dir

        def read_text(self, filename):
            path = f"{self._metadata_dir}/{filename}"
            contents = _read_blob_file(path)
            if contents is None:
                return None
            return contents.decode("utf-8")

        def locate_file(self, path):
            from pathlib import PurePosixPath

            return PurePosixPath(
                f"{_ZIPPY_SENTINEL}{self._metadata_dir}/{path}"
            )

    _zippy_distribution_type = ZippyDistribution
    return _zippy_distribution_type


class _ZippyDistributionFinder:
    def find_spec(self, fullname, path=None, target=None):
        return None

    def find_distributions(self, context=None):
        distribution_type = _get_zippy_distribution_type()
        requested_name = getattr(context, "name", None)
        normalized_request = (
            _normalize_distribution_name(requested_name)
            if requested_name is not None
            else None
        )
        for child in _list_blob_dir(""):
            if not child.endswith(".dist-info"):
                continue
            distribution = distribution_type(child)
            if normalized_request is not None:
                metadata_name = distribution.metadata.get("Name")
                if (
                    metadata_name is None
                    or _normalize_distribution_name(metadata_name)
                    != normalized_request
                ):
                    continue
            yield distribution


# First, so a system platlib on sys.path cannot shadow the metadata of the
# packages the payload actually loads.
sys.meta_path.insert(0, _ZippyDistributionFinder())


# ---- Wizard subsystem: serve definitions from the blob ----
# WIZARD_SPEC_DIR is computed from __file__ at import time, which produces a
# synthetic path in the embedded runtime. Point the loader at the packed AWS
# CLI catalog and adapt its filesystem operations to the in-memory finder.
_ZIPPY_WIZARD_DIR = "__ZIPPY__/awscli/customizations/wizard/wizards"
_wizard_loader_patched = False


def _patch_wizard_loader(_wizard_loader):
    global _wizard_loader_patched
    if _wizard_loader_patched:
        return

    _orig_wizard_list_commands = _wizard_loader.WizardLoader.list_commands_with_wizards
    _orig_wizard_list_available = _wizard_loader.WizardLoader.list_available_wizards
    _orig_wizard_exists = _wizard_loader.WizardLoader.wizard_exists
    _orig_wizard_load = _wizard_loader.WizardLoader.load_wizard

    def _patched_wizard_list_commands(self):
        if self._spec_dir == _ZIPPY_WIZARD_DIR:
            return _list_blob_dir(self._spec_dir)
        return _orig_wizard_list_commands(self)

    def _patched_wizard_list_available(self, command_name):
        if self._spec_dir == _ZIPPY_WIZARD_DIR:
            files = _list_blob_dir(f"{self._spec_dir}/{command_name}")
            return [os.path.splitext(filename)[0] for filename in files]
        return _orig_wizard_list_available(self, command_name)

    def _patched_wizard_exists(self, command_name, wizard_name):
        if self._spec_dir == _ZIPPY_WIZARD_DIR:
            path = f"{self._spec_dir}/{command_name}/{wizard_name}.yml"
            return _blob_isfile(path)
        return _orig_wizard_exists(self, command_name, wizard_name)

    def _patched_wizard_load(self, command_name, wizard_name):
        if self._spec_dir == _ZIPPY_WIZARD_DIR:
            path = f"{self._spec_dir}/{command_name}/{wizard_name}.yml"
            contents = _read_blob_file(path)
            if contents is not None:
                return self._load_yaml(contents.decode("utf-8"))
            raise _wizard_loader.WizardNotExistError(
                "Wizard does not exist for command "
                "'%s', name: '%s'" % (command_name, wizard_name)
            )
        return _orig_wizard_load(self, command_name, wizard_name)

    _wizard_loader.WIZARD_SPEC_DIR = _ZIPPY_WIZARD_DIR
    _wizard_loader.WizardLoader.list_commands_with_wizards = _patched_wizard_list_commands
    _wizard_loader.WizardLoader.list_available_wizards = _patched_wizard_list_available
    _wizard_loader.WizardLoader.wizard_exists = _patched_wizard_exists
    _wizard_loader.WizardLoader.load_wizard = _patched_wizard_load
    _wizard_loader_patched = True


def _zippy_register_wizard_commands(event_handlers):
    import awscli.customizations.wizard.loader as _wizard_loader
    _patch_wizard_loader(_wizard_loader)
    from awscli.customizations.wizard import commands as _wizard_commands
    return _wizard_commands.register_wizard_commands(event_handlers)


def _zippy_register_add_waiters(event_handlers):
    def _lazy_add_waiters(command_table, session, command_object, **kwargs):
        service_model = getattr(command_object, "service_model", None)
        if service_model is None:
            return
        from awscli.customizations import waiters as _waiters
        return _waiters.add_waiters(
            command_table=command_table,
            session=session,
            command_object=command_object,
            **kwargs,
        )

    event_handlers.register("building-command-table", _lazy_add_waiters)


_ZIPPY_EXAMPLES_DIR = "__ZIPPY__/awscli/examples"
_ZIPPY_TOPICS_DIR = "__ZIPPY__/awscli/topics"
_help_modules_patched = False


def _open_zippy_topic(filename, *args, **kwargs):
    if isinstance(filename, str) and filename.startswith(_ZIPPY_TOPICS_DIR):
        mode = args[0] if args else kwargs.get("mode", "r")
        if mode in ("r", "rt"):
            data = _read_blob_file(filename)
            if data is not None:
                encoding = kwargs.get("encoding") or "utf-8"
                errors = kwargs.get("errors") or "strict"
                return _io.StringIO(data.decode(encoding, errors))
    return _builtins.open(filename, *args, **kwargs)


def _patch_windows_pager_fallback(_help):
    """Print the help document when the configured pager can't be launched.

    ``PosixPagingHelpRenderer._send_output_to_pager`` looks its pager up on
    PATH first and writes the raw document to stdout when it isn't there. The
    Windows renderers have no such fallback: they hand the pager to ``cmd /c``
    (``shell=True``) and never look at the child, so any pager cmd.exe can't
    start -- ``MANPAGER=/bin/cat``, or a ``PAGER`` exported by a shell profile
    whose executable isn't on the native PATH -- sends the whole document into
    a dead pipe while ``aws help ...`` still exits 0 with no output at all.

    Give the Windows renderers that same fallback. The lookup goes through
    ``shutil.which`` rather than upstream's ``_exists_on_path``, which
    deliberately ignores PATHEXT: on Windows the default pager ``more`` is
    ``more.COM``, so a plain path join would report even the working default
    as missing and route every help command through the fallback.

    Only the Windows renderer is patched (``WindowsHelpRenderer`` inherits
    it), so POSIX keeps upstream's own fallback. A nonzero exit from a pager
    that did start is deliberately left alone: it is indistinguishable from a
    user quitting the pager early, and reprinting the document underneath what
    the pager already displayed would be worse than the status quo.
    """

    def _send_output_to_pager(self, output):
        import shutil
        from subprocess import PIPE

        cmdline = self.get_pager_cmdline()
        process = None
        if cmdline and shutil.which(cmdline[0]) is not None:
            try:
                process = self._popen(cmdline, stdin=PIPE)
            except OSError:
                process = None
        if process is None:
            _help.LOG.debug(
                "Pager %s could not be launched, printing raw help.", cmdline
            )
            buffer = getattr(self.output_stream, "buffer", None)
            if buffer is not None:
                self.output_stream.flush()
                buffer.write(output + b"\n")
                buffer.flush()
            else:
                self.output_stream.write(output.decode("utf-8") + "\n")
                self.output_stream.flush()
            return
        process.communicate(input=output)

    _help.WindowsPagingHelpRenderer._send_output_to_pager = (
        _send_output_to_pager
    )


def _patch_help_modules():
    global _help_modules_patched
    if _help_modules_patched:
        return

    import awscli.clidocs as _clidocs
    import awscli.topictags as _topictags
    import awscli.customizations.commands as _commands

    _orig_get_doc_contents = _commands.BasicHelp._get_doc_contents

    def _patched_get_doc_contents(
        self: _commands.BasicHelp, attr_name: str,
    ) -> str:
        value = getattr(self, attr_name)
        if not isinstance(value, _commands.BasicCommand.FROM_FILE):
            return _orig_get_doc_contents(self, attr_name)
        module_file = getattr(value.root_module, "__file__", "")
        if not (
            isinstance(module_file, str)
            and module_file.startswith(_SYNTHETIC_ROOT)
        ):
            return _orig_get_doc_contents(self, attr_name)

        trailing_path = value.filename
        if trailing_path is None:
            trailing_path = os.path.join(self.name, f"{attr_name}.rst")
        module_path = module_file[len(_SYNTHETIC_ROOT):]
        blob_key = os.path.join(
            os.path.dirname(module_path), "examples", trailing_path,
        ).replace(os.sep, "/")
        return _zippy_finder.get_data(blob_key).decode("utf-8")

    _commands.BasicHelp._get_doc_contents = _patched_get_doc_contents

    _clidocs.EXAMPLES_DIR = _ZIPPY_EXAMPLES_DIR
    _clidocs.GLOBAL_OPTIONS_FILE = _ZIPPY_EXAMPLES_DIR + "/global_options.rst"
    _clidocs.GLOBAL_OPTIONS_SYNOPSIS_FILE = _ZIPPY_EXAMPLES_DIR + "/global_synopsis.rst"

    _orig_topic_tag_db_init = _topictags.TopicTagDB.__init__

    def _patched_topic_tag_db_init(
        self,
        tag_dictionary=None,
        index_file=_ZIPPY_TOPICS_DIR + "/topic-tags.json",
        topic_dir=_ZIPPY_TOPICS_DIR,
    ):
        _orig_topic_tag_db_init(self, tag_dictionary, index_file, topic_dir)

    _topictags.TopicTagDB.TOPIC_DIR = _ZIPPY_TOPICS_DIR
    _topictags.TopicTagDB.JSON_INDEX = _ZIPPY_TOPICS_DIR + "/topic-tags.json"
    _topictags.TopicTagDB.__init__ = _patched_topic_tag_db_init
    _topictags.open = _open_zippy_topic
    _clidocs.open = _open_zippy_topic

    import awscli.bcdoc.restdoc as _restdoc
    _orig_write_from_file = _restdoc.ReSTDocument.write_from_file

    def _patched_write_from_file(self, filename):
        if isinstance(filename, str) and filename.startswith("__ZIPPY__/"):
            blob_key = filename[len("__ZIPPY__/"):]
            try:
                data = _zippy_finder.get_data(blob_key)
            except FileNotFoundError:
                return
            for line in data.decode("utf-8").splitlines():
                self.writeln(line.strip())
            return
        return _orig_write_from_file(self, filename)

    _restdoc.ReSTDocument.write_from_file = _patched_write_from_file

    import awscli.help as _real_help
    _patch_windows_pager_fallback(_real_help)

    _help_modules_patched = True

_EXAMPLES_HELP_NOTE = (
    "<p>To use the following examples, you must have the AWS CLI installed "
    "and configured. See the "
    "<a href='https://docs.aws.amazon.com/cli/latest/userguide/"
    "cli-chap-getting-started.html'>Getting started guide</a> in the "
    "<i>AWS CLI User Guide</i> for more information.</p>"
    "<p>Unless otherwise stated, all examples have unix-like quotation "
    "rules. These examples will need to be adapted to your terminal's "
    "quoting rules. See "
    "<a href='https://docs.aws.amazon.com/cli/latest/userguide/"
    "cli-usage-parameters-quoting-strings.html'>"
    "Using quotation marks with strings</a> "
    "in the <i>AWS CLI User Guide</i>.</p>"
)


def _patched_add_examples(help_command, **kwargs):
    rel = help_command.event_class.replace(".", "/") + ".rst"
    try:
        data = _zippy_finder.get_data("awscli/examples/" + rel)
    except FileNotFoundError:
        return
    help_command.doc.style.h2("Examples")
    help_command.doc.style.start_note()
    help_command.doc.include_doc_string(_EXAMPLES_HELP_NOTE)
    help_command.doc.style.end_note()
    for line in data.decode("utf-8").splitlines(keepends=True):
        help_command.doc.write(line)


def _zippy_register_docs_add_examples(event_emitter):
    event_emitter.register("doc-examples.*.*", _patched_add_examples)


_zippy_hooks = _types.ModuleType(_ZIPPY_HOOKS_MODULE)
_zippy_hooks.register_wizard_commands = _zippy_register_wizard_commands
_zippy_hooks.register_add_waiters = _zippy_register_add_waiters
_zippy_hooks.register_docs_add_examples = _zippy_register_docs_add_examples
sys.modules[_ZIPPY_HOOKS_MODULE] = _zippy_hooks


import awscli.clidriver as _clidriver
from awscli.botocore.compat import OrderedDict as _OrderedDict


class _LazyServiceCommandTable(_OrderedDict):
    _UNMATERIALIZED = object()

    def __init__(self, session, service_names):
        super().__init__(
            (service_name, self._UNMATERIALIZED)
            for service_name in service_names
        )
        self._session = session

    def _materialize(self, service_name, value):
        if value is self._UNMATERIALIZED:
            value = _clidriver.ServiceCommand(
                cli_name=service_name,
                session=self._session,
                service_name=service_name,
            )
            _OrderedDict.__setitem__(self, service_name, value)
        return value

    def __getitem__(self, service_name):
        value = _OrderedDict.__getitem__(self, service_name)
        return self._materialize(service_name, value)

    def get(self, service_name, default=None):
        if service_name not in self:
            return default
        return self[service_name]

    def items(self):
        for service_name in list(_OrderedDict.keys(self)):
            yield service_name, self[service_name]

    def values(self):
        for service_name in list(_OrderedDict.keys(self)):
            yield self[service_name]


def _zippy_build_builtin_commands(self, session):
    return _LazyServiceCommandTable(
        self.session,
        session.get_available_services(),
    )


_clidriver.CLIDriver._build_builtin_commands = _zippy_build_builtin_commands


# ---- User-Agent version and metadata the host sets ----
# The runner publishes the version the host names itself by, or None to keep
# upstream's __version__, and the md/ components it adds to every request's
# User-Agent, such as why the native router handed the invocation to Python
# (crates/python-fallback/src/runner.rs), as (name, value) pairs. The CLI
# sets up the User-Agent of each session its drivers create in
# _set_user_agent_for_session, so the version replaces the one it sets there,
# which `aws --version` prints too, and each pair follows the extras it adds.
from awscli.utils import add_metadata_component_to_user_agent_extra

_user_agent_version = sys._zippy_user_agent_version
del sys._zippy_user_agent_version
_user_agent_metadata = sys._zippy_user_agent_metadata
del sys._zippy_user_agent_metadata
_orig_set_user_agent_for_session = _clidriver._set_user_agent_for_session


def _zippy_set_user_agent_for_session(session):
    _orig_set_user_agent_for_session(session)
    if _user_agent_version is not None:
        session.user_agent_version = _user_agent_version
    for name, value in _user_agent_metadata:
        add_metadata_component_to_user_agent_extra(session, name, value)


_clidriver._set_user_agent_for_session = _zippy_set_user_agent_for_session


sys.exit(_clidriver.main())
