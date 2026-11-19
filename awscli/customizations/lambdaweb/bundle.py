# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import fnmatch
import logging
import os
import re
import stat
import tempfile
import time
import zipfile

from awscli.customizations.lambdaweb import output
from awscli.customizations.lambdaweb.constants import (
    DEFAULT_INCLUDED_HIDDEN_DIRECTORIES,
    DEFAULT_INCLUDED_HIDDEN_FILES,
    FUNCTION_NAME_PATTERN,
)
from awscli.customizations.lambdaweb.exceptions import (
    InvalidFunctionNameError,
    InvalidSourceError,
    WrapperConflictError,
)
from awscli.customizations.lambdaweb.utils import posix_relpath

logger = logging.getLogger(__name__)


_FUNCTION_NAME_RE = re.compile(FUNCTION_NAME_PATTERN)


def _normalize_force_include(source_dir, paths):
    """Return validated ``--force-include`` paths in ZIP path form."""
    normalized_paths = set()
    for path in paths or ():
        normalized = os.path.normpath(path)
        if (
            not path
            or os.path.isabs(path)
            or normalized in ('.', '..')
            or normalized.startswith(f'..{os.sep}')
        ):
            raise InvalidSourceError(
                f"--force-include path '{path}' must be relative to --code "
                'and remain inside that directory.'
            )
        full_path = os.path.join(source_dir, normalized)
        if os.path.islink(full_path) or not os.path.isfile(full_path):
            raise InvalidSourceError(
                f"--force-include path '{path}' must identify a regular file "
                f"under --code '{source_dir}'. Directories, symlinks, and "
                "special files aren't supported."
            )
        normalized_paths.add(posix_relpath(normalized))
    return normalized_paths


def _is_hidden(name):
    """Return True for a dotfile / dot-dir basename (but not '.'/'..')."""
    return name.startswith('.') and name not in ('.', '..')


def _inside_included_hidden_directory(rel_root):
    """Return True inside a hidden directory included by default."""
    if rel_root == '.':
        return False
    return any(
        part in DEFAULT_INCLUDED_HIDDEN_DIRECTORIES
        for part in rel_root.split('/')
    )


def _excluded(name, relpath, patterns):
    """Return True if a path component or its full relative path is excluded.

    ``name`` is the bare basename (dir or file); ``relpath`` is the path
    relative to the source root, with ``/`` separators. Single-segment
    patterns (``.git/``, ``*.pem``) are matched against the basename;
    multi-segment patterns (``node_modules/.cache/``) are matched against the
    full relative path or a suffix beginning at a path-component boundary.
    """
    for pat in patterns:
        check = pat.rstrip('/') if pat.endswith('/') else pat
        if not check:
            continue
        target = relpath if '/' in check else name
        # match case-insensitively on every platform so security patterns
        # like .env / *.pem cannot be bypassed with a different case on
        # case-sensitive filesystems.
        target = target.lower()
        check = check.lower()
        if fnmatch.fnmatch(target, check):
            return True
        if '/' in check and fnmatch.fnmatch(target, f'*/{check}'):
            return True
    return False


_SYMLINK_WARN_SAMPLE = 5
_HIDDEN_WARN_SAMPLE = 5


def _warn_skipped_symlinks(skipped_links, symlink_hint=None):
    """Emit ONE consolidated warning naming symlinks left out of the bundle.

    Kept separate from the walk so ``build_zip`` reads cleanly and this stays
    unit-testable. No-op when nothing was skipped. Names up to
    :data:`_SYMLINK_WARN_SAMPLE` paths and appends the runtime's
    ``symlink_hint`` sentence, which says how to materialize dependency
    links for that language.
    """
    if not skipped_links:
        return
    sample = skipped_links[:_SYMLINK_WARN_SAMPLE]
    listed = ', '.join(sample)
    if len(skipped_links) > _SYMLINK_WARN_SAMPLE:
        listed += f', ... and {len(skipped_links) - _SYMLINK_WARN_SAMPLE} more'
    message = (
        f'Warning: skipped {len(skipped_links)} symlink(s) not followed into '
        f'the bundle: {listed}. Symlinks are never followed (they can escape '
        'the source directory or form cycles).'
    )
    if symlink_hint:
        message = f'{message} {symlink_hint}'
    output.progress(message)


def _warn_skipped_hidden_paths(skipped_paths):
    """Emit one warning for hidden files and directories left out."""
    if not skipped_paths:
        return
    sample = skipped_paths[:_HIDDEN_WARN_SAMPLE]
    listed = ', '.join(sample)
    if len(skipped_paths) > _HIDDEN_WARN_SAMPLE:
        listed += f', ... and {len(skipped_paths) - _HIDDEN_WARN_SAMPLE} more'
    noun = 'path' if len(skipped_paths) == 1 else 'paths'
    output.progress(
        f'Warning: skipped {len(skipped_paths)} hidden {noun}: {listed}. '
        'Use --include-hidden-files to include hidden files and directories '
        "that don't match an exclusion pattern."
    )


def _warn_force_includes(paths):
    """Warn when files bypass the normal bundle exclusions."""
    if not paths:
        return
    listed = ', '.join(sorted(paths))
    output.progress(
        'Warning: The command includes these files as requested by '
        f'--force-include: {listed}. Verify that '
        "these files don't contain credentials or other secrets. Use AWS "
        'Secrets Manager for runtime secrets.'
    )


def _keep_dir(
    root,
    rel_root,
    name,
    exclude_patterns,
    include_hidden,
    skipped_links,
    skipped_hidden_paths,
):
    """Decide whether ``os.walk`` should descend into ``name``.

    Explicit exclusions take precedence. Included hidden directories and their
    descendants do not require the general hidden-file opt-in.
    """
    relpath = name if rel_root == '.' else f'{rel_root}/{name}'
    if _excluded(name, relpath, exclude_patterns):
        return False
    if (
        not include_hidden
        and _is_hidden(name)
        and name not in DEFAULT_INCLUDED_HIDDEN_DIRECTORIES
        and not _inside_included_hidden_directory(rel_root)
    ):
        skipped_hidden_paths.append(relpath)
        return False
    if os.path.islink(os.path.join(root, name)):
        # os.walk lists symlinked dirs under ``dirs`` even with
        # followlinks=False; prune so we neither descend nor add them, and
        # record the skip for the summary warning.
        skipped_links.append(relpath)
        return False
    return True


def build_zip(
    source_dir,
    selection,
    exclude_patterns,
    include_hidden,
    force_include=None,
    symlink_hint=None,
):
    """Build a zip from ``source_dir`` and return ``(temp_path, size)``.

    ``selection`` is the runtime's ``EntrySelection``. Its ``bundle_path``
    must end up in the package, and its ``wrapper`` file, if any, is added
    to the package. Pass ``None`` to package the tree as-is.

    ``exclude_patterns`` excludes secrets, VCS metadata, and caches by default.
    ``force_include`` can override file exclusions for exact regular files,
    but it does not override hidden or excluded directories, symlinks, or
    special-file checks. Common hidden build and runtime paths are included by
    default. ``include_hidden`` controls other dotfiles and dot-directories.
    """
    forced_files = _normalize_force_include(source_dir, force_include)
    tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    tmp.close()
    temp_path = tmp.name
    try:
        _write_zip(
            temp_path,
            source_dir,
            selection,
            exclude_patterns,
            include_hidden,
            forced_files,
            symlink_hint,
        )
    except BaseException:
        remove_bundle(temp_path)
        raise
    return temp_path, os.path.getsize(temp_path)


def remove_bundle(zip_path):
    """Delete a bundle produced by ``build_zip``; missing files are fine."""
    try:
        os.unlink(zip_path)
    except OSError:
        logger.debug('could not remove bundle %s', zip_path, exc_info=True)


def _write_zip(
    temp_path,
    source_dir,
    selection,
    exclude_patterns,
    include_hidden,
    forced_files,
    symlink_hint=None,
):
    # Collect skipped symlinks; _warn_skipped_symlinks emits a summary after the walk.
    skipped_links = []
    skipped_hidden_paths = []
    bundled_paths = set()
    with zipfile.ZipFile(
        temp_path, mode='w', compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for root, dirs, files in os.walk(source_dir, followlinks=False):
            rel_root = os.path.relpath(root, source_dir).replace(os.sep, '/')
            dirs[:] = [
                d
                for d in dirs
                if _keep_dir(
                    root,
                    rel_root,
                    d,
                    exclude_patterns,
                    include_hidden,
                    skipped_links,
                    skipped_hidden_paths,
                )
            ]
            for fn in files:
                full = os.path.join(root, fn)
                relpath = fn if rel_root == '.' else f'{rel_root}/{fn}'
                is_forced = relpath in forced_files
                if not is_forced and _excluded(fn, relpath, exclude_patterns):
                    continue
                if (
                    not is_forced
                    and not include_hidden
                    and _is_hidden(fn)
                    and fn not in DEFAULT_INCLUDED_HIDDEN_FILES
                    and not _inside_included_hidden_directory(rel_root)
                ):
                    skipped_hidden_paths.append(relpath)
                    continue
                if os.path.islink(full):
                    logger.debug('skipping symlink %s', full)
                    skipped_links.append(relpath)
                    continue
                if not os.path.isfile(full):
                    # FIFOs, sockets, and device nodes cannot be bundled --
                    # reading a FIFO would block the CLI forever.
                    output.progress(
                        f'Warning: skipping {relpath}: not a regular file.'
                    )
                    continue
                arcname = relpath
                zf.write(full, arcname)
                bundled_paths.add(arcname)
        missing_forced = sorted(forced_files - bundled_paths)
        if missing_forced:
            listed = ', '.join(f"'{path}'" for path in missing_forced)
            raise InvalidSourceError(
                "The command couldn't include these --force-include paths: "
                f'{listed}. Use --include-hidden-files if a parent directory '
                "is hidden. Files inside excluded or symlinked directories "
                "can't be included."
            )
        _warn_skipped_hidden_paths(skipped_hidden_paths)
        _warn_skipped_symlinks(skipped_links, symlink_hint)
        entry = selection.bundle_path if selection is not None else None
        if entry is not None and posix_relpath(entry) not in bundled_paths:
            raise InvalidSourceError(
                f"entry point '{entry}' is not included in the deployment "
                'bundle. It may be hidden, excluded, a symlink, or not a '
                'regular file. Choose an included file, use '
                '--force-include for an excluded file, or use '
                '--include-hidden-files for a hidden file.'
            )
        wrapper = selection.wrapper if selection is not None else None
        if wrapper is not None:
            arcname, content = wrapper
            if arcname in bundled_paths:
                existing = os.path.join(source_dir, arcname)
                raise WrapperConflictError(
                    f"Cannot inject wrapper: '{existing}' already exists. "
                    f'Either rename your entry point to {arcname}, or '
                    f'remove the existing {arcname} from the source '
                    'directory.'
                )
            zf.writestr(_wrapper_zipinfo(arcname), content)

        _warn_force_includes(forced_files)


def _wrapper_zipinfo(arcname):
    # writestr's default entry mode is 0600, which the runtime may not be
    # able to read after extraction; give the wrapper world-readable 0644.
    info = zipfile.ZipInfo(arcname, date_time=time.localtime()[:6])
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def validate_function_name(name):
    """Raise ``InvalidFunctionNameError`` for an invalid web function name."""
    if not isinstance(name, str) or not _FUNCTION_NAME_RE.match(name):
        raise InvalidFunctionNameError(
            f"function name '{name}' is invalid: must be 2-64 characters, "
            'only alphanumeric, hyphens, and underscores, '
            'and must not start or end with a hyphen or underscore'
        )
