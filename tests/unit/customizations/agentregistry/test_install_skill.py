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
"""install-skill: download URL checks, name safety, extraction, replacement."""

import argparse
import hashlib
import hmac
import http.client
import io
import json
import logging
import os
import pathlib
import stat
import urllib.error
import zipfile
from unittest.mock import Mock, patch

import botocore.loaders
import botocore.session
import pytest

from awscli.customizations.agentregistry import (
    cache,
    dataplane,
    install_skill,
    providers,
    utils,
)
from awscli.customizations.agentregistry.install_skill import (
    PROVENANCE_MARKER,
    InstallSkillCommand,
    is_s3_host,
    is_spec_skill_name,
    skill_path,
    validate_download_url,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.utils import AGENT_ARG
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agentregistry.utils import (
    make_agents,
    make_skill_md,
    make_zip,
)

posix_only = pytest.mark.skipif(os.name == 'nt', reason='POSIX modes')


def _on_windows(monkeypatch, windows=True):
    """Apply the Windows-only name checks, or not, whatever the system."""
    monkeypatch.setattr(install_skill, '_ON_WINDOWS', windows)


S3_URL = (
    'https://bucket.s3.us-west-2.amazonaws.com/pkg.zip'
    '?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAEXAMPLE'
    '&X-Amz-Security-Token=IQoJsession&X-Amz-Signature=deadbeef'
)
ENDPOINT = 'https://agent-registry.us-west-2.api.aws'


def _assert_no_query(message):
    for secret in ('X-Amz', 'ASIAEXAMPLE', 'IQoJsession', 'deadbeef'):
        assert secret not in message


REGISTRY_ID = 'abcDEF123456'
REGISTRY_ARN = (
    f'arn:aws:agent-registry:us-west-2:123456789012:registry/{REGISTRY_ID}'
)


# --- Download URL -----------------------------------------------------------


@pytest.mark.parametrize(
    'host,region',
    [
        ('bucket.s3.us-west-2.amazonaws.com', 'us-west-2'),
        ('s3.us-west-2.amazonaws.com', 'us-west-2'),
        ('my.dotted.bucket.s3.us-west-2.amazonaws.com', 'us-west-2'),
        ('bucket.s3.dualstack.us-west-2.amazonaws.com', 'us-west-2'),
        ('bucket.s3-fips.us-west-2.amazonaws.com', 'us-west-2'),
        (
            'ap-123456789012.s3-accesspoint.us-west-2.amazonaws.com',
            'us-west-2',
        ),
        ('bucket.s3-us-west-2.amazonaws.com', 'us-west-2'),
        ('bucket.s3.amazonaws.com', 'us-east-1'),
        ('bucket.s3.cn-north-1.amazonaws.com.cn', 'cn-north-1'),
        ('BUCKET.S3.US-WEST-2.AMAZONAWS.COM', 'us-west-2'),
    ],
)
def test_s3_hosts_are_accepted(host, region):
    assert is_s3_host(host, region)


@pytest.mark.parametrize(
    'host,region',
    [
        ('evil.example', 'us-west-2'),
        ('s3.us-west-2.amazonaws.com.evil.example', 'us-west-2'),
        ('bucket.s3.us-east-1.amazonaws.com', 'us-west-2'),
        ('bucket.s3.amazonaws.com', 'us-west-2'),
        ('amazonaws.com', 'us-west-2'),
        ('bucket.nots3.us-west-2.amazonaws.com', 'us-west-2'),
        ('bucket.s3.us-west-2.amazonaws.com.cn.evil', 'us-west-2'),
        ('bucket.execute-api.us-west-2.amazonaws.com', 'us-west-2'),
        ('', 'us-west-2'),
        (None, 'us-west-2'),
    ],
)
def test_non_s3_hosts_are_rejected(host, region):
    assert not is_s3_host(host, region)


@pytest.mark.parametrize(
    'url',
    [
        'http://bucket.s3.us-west-2.amazonaws.com/pkg.zip',
        'file:///etc/passwd',
        'https://evil.example/pkg.zip',
        'https://bucket.s3.us-east-1.amazonaws.com/pkg.zip',
    ],
)
def test_download_url_validation_rejects(url):
    with pytest.raises(AgentRegistryJWTError):
        validate_download_url(url, 'us-west-2')


@pytest.mark.parametrize(
    'url',
    [
        S3_URL.replace('bucket.s3.us-west-2', 'bucket.s3.us-east-1'),
        S3_URL.replace(
            'https://bucket.s3.us-west-2.amazonaws.com', 'https://evil.example'
        ),
        S3_URL.replace('https://', 'http://'),
    ],
)
def test_refused_download_url_is_shown_without_its_query(url):
    with pytest.raises(AgentRegistryJWTError) as e:
        validate_download_url(url, 'us-west-2')
    _assert_no_query(str(e.value))


def _response(chunks):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read = Mock(side_effect=chunks)
    return response


@pytest.mark.parametrize(
    'error',
    [
        # A body, as urllib gives: on Python 3.9 an HTTPError without one
        # raises KeyError for any attribute it lacks, which pytest probes
        urllib.error.HTTPError(S3_URL, 403, 'Forbidden', {}, io.BytesIO()),
        urllib.error.HTTPError(S3_URL, 500, 'Server Error', {}, io.BytesIO()),
        urllib.error.URLError(f'could not reach {S3_URL}'),
        AgentRegistryJWTError(
            'Refusing to follow a redirect (HTTP 302) from '
            'https://bucket.s3.us-west-2.amazonaws.com.'
        ),
    ],
    ids=['http-403', 'http-500', 'url-error', 'redirect'],
)
def test_download_errors_do_not_repeat_the_presigned_url(tmp_path, error):
    with patch.object(install_skill, 'urlopen', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            InstallSkillCommand(Mock())._download(S3_URL, str(tmp_path / 'a'))
    message = str(e.value)
    assert 'https://bucket.s3.us-west-2.amazonaws.com' in message
    if getattr(error, 'code', None) == 403:
        assert 'may have expired' in message
    for secret in ('ASIAEXAMPLE', 'IQoJsession', 'deadbeef'):
        assert secret not in message


def test_download_uses_the_no_redirect_https_opener(tmp_path):
    response = _response([b'abc', b''])
    with patch.object(
        install_skill, 'urlopen', return_value=response
    ) as opened:
        InstallSkillCommand(Mock())._download(
            S3_URL, str(tmp_path / 'a.zip'), '/corp.pem'
        )
    assert opened.call_args.args[0] == S3_URL
    assert opened.call_args.kwargs['purpose'] == 'download URL'
    assert opened.call_args.kwargs['ca_bundle'] == '/corp.pem'
    assert (tmp_path / 'a.zip').read_bytes() == b'abc'


def test_download_stops_at_the_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(install_skill, 'MAX_ARCHIVE_BYTES', 4)
    response = _response([b'abc', b'def', b''])
    with patch.object(install_skill, 'urlopen', return_value=response):
        with pytest.raises(AgentRegistryJWTError, match='exceeds'):
            InstallSkillCommand(Mock())._download(S3_URL, str(tmp_path / 'a'))


# --- Skill name -------------------------------------------------------------


@pytest.mark.parametrize(
    'name', ['pdf-extract', 'a', '7', 'a1-b2-c3', '0-x', 'x' * 64]
)
def test_valid_skill_names(name):
    assert is_spec_skill_name(name)


# Not in the Agent Skills specification's form.
_INVALID_SKILL_NAMES = [
    'Skill',
    'PDF-extract',
    'pdf_extract',
    'pdf.extract',
    'x' * 65,
    '-pdf',
    'pdf-',
    'pdf--extract',
    '-',
    'a/../../..',
    '../x',
    '..',
    '.',
    '.hidden',
    '/abs',
    'a/b',
    'a\\b',
    'a b',
    '',
    None,
    'name\x00',
    'name\n',
    'name\r',
    7,
    'pdf-extract ',
    # Lookalikes of ASCII letters.
    'p\u0430f',
    'ｐｄｆ',
]


@pytest.mark.parametrize('name', _INVALID_SKILL_NAMES)
@pytest.mark.parametrize('windows', [True, False])
def test_names_outside_the_specification_are_not_skill_names(
    monkeypatch, name, windows
):
    _on_windows(monkeypatch, windows)
    assert not is_spec_skill_name(name)


# Windows device names in the specification's form: Windows reads them as a
# device rather than a folder.
_WINDOWS_SKILL_NAMES = [
    'con',
    'prn',
    'aux',
    'nul',
    'com1',
    'com9',
    'lpt1',
    'lpt9',
]


@pytest.mark.parametrize('name', _WINDOWS_SKILL_NAMES)
def test_windows_skill_names_are_refused_on_windows(monkeypatch, name):
    _on_windows(monkeypatch)
    assert not is_spec_skill_name(name)
    with pytest.raises(AgentRegistryJWTError, match='device name'):
        install_skill.safe_folder_name(name)


@pytest.mark.parametrize('name', _WINDOWS_SKILL_NAMES)
def test_windows_skill_names_are_allowed_elsewhere(monkeypatch, name):
    _on_windows(monkeypatch, False)
    assert is_spec_skill_name(name)


@pytest.mark.parametrize(
    'name', ['console', 'config', 'com0', 'com10', 'lpt', 'nul-skill', 'con-1']
)
@pytest.mark.parametrize('windows', [True, False])
def test_names_that_merely_resemble_device_names_are_allowed(
    monkeypatch, name, windows
):
    _on_windows(monkeypatch, windows)
    assert is_spec_skill_name(name)


def test_device_name_is_refused_before_anything_is_touched(
    monkeypatch, tmp_path
):
    _on_windows(monkeypatch)
    with pytest.raises(AgentRegistryJWTError, match='device name'):
        skill_path(str(tmp_path), 'nul')


def test_skill_path_is_a_direct_child_of_the_target(tmp_path):
    assert skill_path(str(tmp_path), 'ok') == os.path.join(
        os.path.realpath(tmp_path), 'ok'
    )


# --- Folder name ------------------------------------------------------------


@pytest.mark.parametrize(
    'name',
    [
        'pdf-tool',
        'pdf_tool',
        'PDF-Tool',
        'pdf.tool',
        'pdf--tool',
        'pdf-',
        '7_x',
        'x' * 64,
    ],
)
@pytest.mark.parametrize('windows', [True, False])
def test_folder_names_accept_spec_and_legacy_names(monkeypatch, name, windows):
    _on_windows(monkeypatch, windows)
    assert install_skill.folder_name_problem(name) is None
    assert install_skill.safe_folder_name(name) == name
    assert skill_path('/skills', name) == os.path.join(
        os.path.realpath('/skills'), name
    )


@pytest.mark.parametrize(
    'name,spec',
    [('pdf-tool', True), ('pdf_tool', False), ('PDF-Tool', False)],
)
def test_is_spec_skill_name_is_the_specification_check(name, spec):
    assert is_spec_skill_name(name) is spec


@pytest.mark.parametrize(
    'name',
    [
        'a/b',
        'a\\b',
        '../x',
        '..',
        '.',
        '.x',
        '.pdf.staging-1234',
        '-x',
        '_x',
        'a b',
        'x ',
        'x' * 65,
        'ünï',
        # A lookalike of an ASCII letter.
        'p\u0430f',
        'name\n',
        'name\x00',
        '',
        None,
        7,
    ],
)
@pytest.mark.parametrize('windows', [True, False])
def test_folder_names_refuse_unsafe(monkeypatch, tmp_path, name, windows):
    _on_windows(monkeypatch, windows)
    assert 'Agent Skills' in install_skill.folder_name_problem(name)
    with pytest.raises(AgentRegistryJWTError, match='Agent Skills'):
        install_skill.safe_folder_name(name)
    with pytest.raises(AgentRegistryJWTError, match='Agent Skills'):
        skill_path(str(tmp_path), name)


def test_folder_name_error_shows_the_name_safely():
    with pytest.raises(AgentRegistryJWTError) as e:
        install_skill.safe_folder_name('a\x1b[2J' + 'b' * 1000)
    message = str(e.value)
    assert '\x1b' not in message
    assert len(message) < 700


@pytest.mark.parametrize(
    'name', ['con', 'CON', 'Nul', 'con.txt', 'LPT1.md', 'x.', 'pdf.tool.']
)
def test_legacy_windows_folder_names_refused_on_windows_only(
    monkeypatch, name
):
    _on_windows(monkeypatch)
    problem = install_skill.folder_name_problem(name)
    assert 'Windows device name such as CON or NUL or end in a dot' in problem
    with pytest.raises(AgentRegistryJWTError, match='device name'):
        install_skill.safe_folder_name(name)
    _on_windows(monkeypatch, False)
    assert install_skill.folder_name_problem(name) is None
    assert install_skill.safe_folder_name(name) == name


@pytest.mark.parametrize('windows', [True, False])
def test_folder_name_error_states_only_this_systems_rules(
    monkeypatch, windows
):
    _on_windows(monkeypatch, windows)
    problem = install_skill.folder_name_problem('a/b')
    assert ('Windows device name' in problem) is windows


# --- Installed copies -------------------------------------------------------


_SOURCE = {
    'registryId': REGISTRY_ID,
    'recordId': 'rec',
    'endpoint': ENDPOINT,
    'sha256': '0' * 64,
}


def _installed_copy(folder, name, **source):
    skill = os.path.join(folder, name)
    os.makedirs(skill)
    with open(os.path.join(skill, 'SKILL.md'), 'w') as f:
        f.write('skill')
    with open(os.path.join(skill, PROVENANCE_MARKER), 'w') as f:
        json.dump(dict(_SOURCE, **source), f)
    return skill


def test_installed_copies_finds_skills_by_marker_whatever_the_name(tmp_path):
    folder = str(tmp_path / 'skills')
    _installed_copy(folder, 'pdf_tool')
    _installed_copy(folder, 'Other-Name')
    _installed_copy(folder, 'other', recordId='rec2')
    root = os.path.realpath(folder)
    copies = install_skill.installed_copies(folder, _SOURCE)
    assert [(name, path) for name, path, _ in copies] == [
        ('Other-Name', os.path.join(root, 'Other-Name')),
        ('pdf_tool', os.path.join(root, 'pdf_tool')),
    ]
    assert copies[0][2] == dict(_SOURCE, content='package')


def test_installed_copies_compares_the_endpoint_as_same_source(tmp_path):
    folder = str(tmp_path / 'skills')
    _installed_copy(
        folder, 'a', endpoint='https://AGENT-REGISTRY.us-west-2.api.aws:443/'
    )
    _installed_copy(
        folder, 'b', endpoint='https://agent-registry.us-east-1.api.aws'
    )
    _installed_copy(folder, 'c', registryId='xyzXYZ9876543210')
    copies = install_skill.installed_copies(folder, _SOURCE)
    assert [name for name, _, _ in copies] == ['a']


def test_installed_copies_skips_what_is_not_an_installed_skill(tmp_path):
    folder = tmp_path / 'skills'
    # Dot-prefixed staging and backup folders, outside the folder-name rule.
    _installed_copy(str(folder), '.pdf.staging-abc')
    _installed_copy(str(folder), '.pdf.old-1234')
    _installed_copy(str(folder), '-pdf')
    # No SKILL.md, no marker, an unreadable marker, a file.
    os.makedirs(folder / 'no-skill-md')
    (folder / 'no-skill-md' / PROVENANCE_MARKER).write_text(
        json.dumps(_SOURCE)
    )
    os.makedirs(folder / 'no-marker')
    (folder / 'no-marker' / 'SKILL.md').write_text('skill')
    bad = _installed_copy(str(folder), 'bad-marker')
    pathlib.Path(bad, PROVENANCE_MARKER).write_text('{not json')
    (folder / 'file').write_text('x')
    assert install_skill.installed_copies(str(folder), _SOURCE) == []


def test_installed_copies_skips_symlinked_folders(tmp_path):
    elsewhere = _installed_copy(str(tmp_path / 'elsewhere'), 'pdf')
    folder = tmp_path / 'skills'
    folder.mkdir()
    os.symlink(elsewhere, folder / 'pdf')
    assert install_skill.installed_copies(str(folder), _SOURCE) == []


def test_installed_copies_follows_a_symlinked_skills_folder(tmp_path):
    real = tmp_path / 'real'
    _installed_copy(str(real), 'pdf')
    os.symlink(real, tmp_path / 'skills')
    [(name, path, _)] = install_skill.installed_copies(
        str(tmp_path / 'skills'), _SOURCE
    )
    assert name == 'pdf'
    assert path == os.path.join(os.path.realpath(real), 'pdf')


def test_installed_copies_skips_an_unparsable_marker_endpoint(tmp_path):
    folder = str(tmp_path / 'skills')
    _installed_copy(folder, 'a', endpoint='https://[broken')
    _installed_copy(folder, 'b')
    copies = install_skill.installed_copies(folder, _SOURCE)
    assert [name for name, _, _ in copies] == ['b']


def test_installed_copies_skips_an_entry_that_cannot_be_read(tmp_path):
    folder = str(tmp_path / 'skills')
    for name in ('a', 'b', 'c'):
        _installed_copy(folder, name)
    real = install_skill.read_provenance

    def failing_for_b(path):
        if os.path.basename(path) == 'b':
            raise PermissionError('denied')
        return real(path)

    with patch.object(
        install_skill, 'read_provenance', side_effect=failing_for_b
    ):
        copies = install_skill.installed_copies(folder, _SOURCE)
    assert [name for name, _, _ in copies] == ['a', 'c']


def test_installed_copies_keeps_what_was_found_if_listing_fails(tmp_path):
    folder = str(tmp_path / 'skills')
    for name in ('a', 'b'):
        _installed_copy(folder, name)
    real_scandir = os.scandir

    class _Failing:
        def __init__(self, path):
            self._entries = real_scandir(path)
            self._first = next(self._entries)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self._entries.close()

        def __iter__(self):
            yield self._first
            raise OSError('I/O error')

    with patch.object(install_skill.os, 'scandir', _Failing):
        copies = install_skill.installed_copies(folder, _SOURCE)
    assert len(copies) == 1


@pytest.mark.parametrize('kind', ['missing', 'file'])
def test_installed_copies_of_a_missing_folder_is_empty(tmp_path, kind):
    folder = tmp_path / 'skills'
    if kind == 'file':
        folder.write_text('x')
    assert install_skill.installed_copies(str(folder), _SOURCE) == []


def test_installed_copies_looks_at_a_bounded_number_of_entries(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(install_skill, 'MAX_SCANNED_ENTRIES', 2)
    folder = str(tmp_path / 'skills')
    for name in ('a', 'b', 'c'):
        _installed_copy(folder, name)
    with patch.object(
        install_skill, 'read_provenance', wraps=install_skill.read_provenance
    ) as read:
        copies = install_skill.installed_copies(folder, _SOURCE)
    assert len(copies) == 2
    assert read.call_count == 2


# --- Extraction -------------------------------------------------------------


def _extract(tmp_path, data):
    archive = tmp_path / 'a.zip'
    archive.write_bytes(data)
    out = tmp_path / 'out'
    install_skill._safe_extract(str(archive), str(out))
    return out


def test_valid_archive_extracts(tmp_path):
    out = _extract(tmp_path, make_zip({'SKILL.md': 'x', 'lib/a.py': 'y'}))
    assert (out / 'SKILL.md').read_text() == 'x'
    assert (out / 'lib' / 'a.py').read_text() == 'y'


@pytest.mark.parametrize(
    'name', ['../escape.txt', 'a/../../escape.txt', '/etc/escape.txt']
)
def test_traversal_and_absolute_entries_are_rejected(tmp_path, name):
    with pytest.raises(AgentRegistryJWTError):
        _extract(tmp_path, make_zip({'SKILL.md': 'x', name: 'evil'}))
    assert not (tmp_path / 'escape.txt').exists()
    assert not (tmp_path / 'out' / 'SKILL.md').exists()


def test_symlink_entries_are_rejected(tmp_path):
    info = zipfile.ZipInfo('link')
    info.external_attr = 0o120777 << 16
    with pytest.raises(AgentRegistryJWTError, match='symlink'):
        _extract(tmp_path, make_zip({'SKILL.md': 'x', info: '/etc/passwd'}))


def test_entry_count_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(install_skill, 'MAX_ENTRIES', 2)
    with pytest.raises(AgentRegistryJWTError, match='entries'):
        _extract(tmp_path, make_zip({'a': '1', 'b': '2', 'c': '3'}))


def test_expanded_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(install_skill, 'MAX_EXTRACTED_BYTES', 10)
    with pytest.raises(AgentRegistryJWTError, match='expands'):
        _extract(tmp_path, make_zip({'SKILL.md': 'x' * 100}))


def test_duplicate_entries_are_rejected(tmp_path):
    archive = make_zip(
        [('SKILL.md', 'x'), ('run.sh', 'safe'), ('run.sh', 'evil')]
    )
    with pytest.raises(AgentRegistryJWTError, match='duplicate'):
        _extract(tmp_path, archive)
    assert not (tmp_path / 'out' / 'run.sh').exists()


@pytest.mark.parametrize(
    'first,second',
    [
        ('lib/Tool.py', 'LIB/tool.py'),
        ('lib/a.py', 'lib//a.py'),
        ('lib/a.py', 'lib/./a.py'),
        # Composed and decomposed forms of the same name.
        ('caf\u00e9.md', 'cafe\u0301.md'),
        ('Stra\u00dfe.md', 'STRASSE.md'),
    ],
)
def test_names_colliding_when_case_is_ignored_are_rejected(
    tmp_path, first, second
):
    archive = make_zip([(first, 'a'), (second, 'b')])
    with pytest.raises(AgentRegistryJWTError, match='collides'):
        _extract(tmp_path, archive)
    assert not os.listdir(tmp_path / 'out')


def _set_encrypted_flag(archive):
    """Mark the archive's only entry as encrypted in both of its headers."""
    data = bytearray(archive)
    local = data.index(b'PK\x03\x04')
    central = data.index(b'PK\x01\x02')
    data[local + 6] |= 0x1
    data[central + 8] |= 0x1
    return bytes(data)


def test_encrypted_entries_are_rejected(tmp_path):
    archive = _set_encrypted_flag(make_zip({'SKILL.md': 'x'}))
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        assert zf.infolist()[0].flag_bits & 0x1
    with pytest.raises(AgentRegistryJWTError, match='encrypted'):
        _extract(tmp_path, archive)
    assert not os.listdir(tmp_path / 'out')


def test_entry_names_are_not_echoed_raw(tmp_path):
    with pytest.raises(AgentRegistryJWTError) as e:
        _extract(tmp_path, make_zip({'../\x1b[2Jx': 'evil'}))
    assert '\x1b' not in str(e.value)


@pytest.mark.parametrize(
    'name',
    [
        'a:b.md',
        'SKILL.md:stream',
        'a<b',
        'a|b',
        'a?b',
        'a*b',
        'a"b',
        'line\nbreak',
        'a\\..\\..\\escape',
    ],
)
@pytest.mark.parametrize('windows', [True, False])
def test_entries_that_are_not_portable_file_names_are_rejected(
    monkeypatch, tmp_path, name, windows
):
    # ZipFile.extractall would rewrite these on Windows; this extractor
    # refuses them everywhere.
    _on_windows(monkeypatch, windows)
    with pytest.raises(AgentRegistryJWTError, match='portable|traversal'):
        _extract(tmp_path, make_zip({'SKILL.md': 'x', name: 'y'}))
    assert not os.listdir(tmp_path / 'out')


# Entry names Windows reads as a device or as another name.
_WINDOWS_ENTRY_NAMES = [
    'lib/CON.py',
    'NUL',
    'aux/x.md',
    'notes./x.md',
    'x.md ',
    # Console devices, and COM and LPT ports with superscript digits.
    'CONIN$',
    'lib/conout$.txt',
    'COM\u00b9',
    'lib/com\u00b2.py',
    'LPT\u00b3.md',
    'CON .txt',
]


@pytest.mark.parametrize('name', _WINDOWS_ENTRY_NAMES)
def test_windows_entry_names_are_rejected_on_windows(
    monkeypatch, tmp_path, name
):
    _on_windows(monkeypatch)
    with pytest.raises(AgentRegistryJWTError, match='portable'):
        _extract(tmp_path, make_zip({'SKILL.md': 'x', name: 'y'}))
    assert not os.listdir(tmp_path / 'out')


@posix_only
@pytest.mark.parametrize('name', _WINDOWS_ENTRY_NAMES)
def test_windows_entry_names_are_extracted_elsewhere(
    monkeypatch, tmp_path, name
):
    _on_windows(monkeypatch, False)
    out = _extract(tmp_path, make_zip({'SKILL.md': 'x', name: 'y'}))
    assert (out / name).read_text() == 'y'


@pytest.mark.parametrize('name', ['./SKILL.md', 'lib/./a.py', 'a.b/c.d'])
def test_dot_segments_and_dotted_names_are_fine(tmp_path, name):
    entries = {name: 'x'}
    if 'SKILL.md' not in name:
        entries['SKILL.md'] = 'x'
    _extract(tmp_path, make_zip(entries))


def _understate(archive, real_size, stated_size):
    """Rewrite both headers of the only entry to declare ``stated_size``."""
    data = bytearray(archive)
    real = real_size.to_bytes(4, 'little')
    stated = stated_size.to_bytes(4, 'little')
    local = data.index(b'PK\x03\x04')
    central = data.index(b'PK\x01\x02')
    assert data[local + 22 : local + 26] == real
    assert data[central + 24 : central + 28] == real
    data[local + 22 : local + 26] = stated
    data[central + 24 : central + 28] = stated
    return bytes(data)


def _deflated(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def test_headers_that_understate_the_size_cannot_bypass_the_cap(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(install_skill, 'MAX_EXTRACTED_BYTES', 1000)
    bomb = _understate(_deflated({'SKILL.md': b'x' * 100_000}), 100_000, 10)
    with zipfile.ZipFile(io.BytesIO(bomb)) as zf:
        assert zf.infolist()[0].file_size == 10
    with pytest.raises(AgentRegistryJWTError):
        _extract(tmp_path, bomb)
    written = sum(
        os.path.getsize(os.path.join(root, name))
        for root, _, names in os.walk(tmp_path / 'out')
        for name in names
    )
    assert written <= 10


class _Endless(io.RawIOBase):
    """An entry stream that produces more than its header declares."""

    def __init__(self, size):
        self._left = size

    def readable(self):
        return True

    def read(self, n=-1):
        n = self._left if n is None or n < 0 else min(n, self._left)
        self._left -= n
        return b'x' * n


def test_bytes_beyond_an_entrys_declared_size_are_refused(tmp_path):
    # Whatever the zip library does, the extractor counts what it writes.
    archive = make_zip({'SKILL.md': 'x' * 10})
    with patch.object(
        zipfile.ZipFile, 'open', return_value=_Endless(1_000_000)
    ):
        with pytest.raises(AgentRegistryJWTError, match='declares'):
            _extract(tmp_path, archive)
    assert os.path.getsize(tmp_path / 'out' / 'SKILL.md') <= 10


def test_bytes_beyond_the_total_cap_are_refused(tmp_path, monkeypatch):
    archive = make_zip({'SKILL.md': 'x' * 60, 'b': 'x' * 60})
    monkeypatch.setattr(install_skill, 'MAX_EXTRACTED_BYTES', 200)
    real_check = install_skill._checked_entries

    def lower_the_cap(zf):
        # As if the declared sizes had passed and the real ones had not.
        infos = real_check(zf)
        monkeypatch.setattr(install_skill, 'MAX_EXTRACTED_BYTES', 100)
        return infos

    with patch.object(
        install_skill, '_checked_entries', side_effect=lower_the_cap
    ):
        with pytest.raises(AgentRegistryJWTError, match='beyond the 100'):
            _extract(tmp_path, archive)


@pytest.mark.parametrize(
    'archive',
    [b'not a zip', make_zip({'SKILL.md': 'x'})[:-30]],
    # The bytes hold a timestamp; xdist workers need identical test ids.
    ids=['not-a-zip', 'truncated'],
)
def test_damaged_archive_is_reported(tmp_path, archive):
    with pytest.raises(AgentRegistryJWTError, match='damaged'):
        _extract(tmp_path, archive)


def _with_mode(name, mode, data='x'):
    info = zipfile.ZipInfo(name)
    info.external_attr = mode << 16
    return info, data


@posix_only
@pytest.mark.parametrize(
    'mode,expected',
    [
        (0o100755, 0o755),
        (0o100775, 0o755),
        (0o100777, 0o755),
        (0o104755, 0o755),  # setuid
        (0o102755, 0o755),  # setgid
        (0o101755, 0o755),  # sticky
        (0o100644, 0o644),
        (0o100666, 0o644),
        (0o100600, 0o600),
        (0o100400, 0o600),
        (0o100500, 0o700),
    ],
)
def test_file_modes_come_from_the_archive_within_0755(
    tmp_path, mode, expected
):
    out = _extract(
        tmp_path, make_zip([('SKILL.md', 'x'), _with_mode('run.sh', mode)])
    )
    assert stat.S_IMODE(os.stat(out / 'run.sh').st_mode) == expected


def test_archive_without_unix_permissions_gets_0644():
    # As made on Windows. Python's own zip writer never records 0.
    info = zipfile.ZipInfo('run.sh')
    info.external_attr = 0x20  # MS-DOS archive bit only
    assert install_skill._file_mode(info) == 0o644


@posix_only
def test_directories_are_0755(tmp_path):
    info = zipfile.ZipInfo('lib/')
    info.external_attr = 0o40777 << 16
    out = _extract(
        tmp_path,
        make_zip([('SKILL.md', 'x'), (info, ''), ('deep/er/a.py', 'y')]),
    )
    for folder in (out, out / 'lib', out / 'deep', out / 'deep' / 'er'):
        assert stat.S_IMODE(os.stat(folder).st_mode) == 0o755


# --- End to end -------------------------------------------------------------


# Zips hold a timestamp, so the default package is built once.
SKILL_MD = make_skill_md()
SKILL_ARCHIVE = make_zip({'SKILL.md': SKILL_MD})


def _command(
    record,
    url=S3_URL,
    archive=None,
    region='us-west-2',
    agent_configs=None,
):
    archive = SKILL_ARCHIVE if archive is None else archive
    record = dict(record)
    record.setdefault('recordId', 'rec')
    record.setdefault(
        'artifact',
        {'sha256': hashlib.sha256(archive).hexdigest(), 'downloadUrl': url},
    )
    client = Mock()
    client.batch_get_discoverable_registry_record.return_value = {
        'registryRecords': [record],
        'errors': [],
    }
    session = Mock()
    session.create_client.return_value = client
    session.get_config_variable.side_effect = {'region': region}.get
    command = InstallSkillCommand(
        session, agent_configs=[] if agent_configs is None else agent_configs
    )

    def download(_url, destination, ca_bundle=None):
        with open(destination, 'wb') as f:
            f.write(archive)

    command._download = Mock(side_effect=download)
    return command, client


def _run(
    command,
    target,
    force=False,
    authorizer=None,
    ca_bundle=None,
    registry_id=REGISTRY_ID,
    verify_ssl=None,
    agent=None,
    record_id='rec',
    client_id=None,
    no_browser=False,
    record_name=None,
):
    args = argparse.Namespace(
        registry_id=registry_id,
        record_id=record_id,
        record_name=record_name,
        target_directory=None if target is None else str(target),
        agent=agent,
        force=force,
        authorizer=authorizer,
        client_id=client_id,
        no_browser=no_browser,
    )
    globals_ = argparse.Namespace(
        region='us-west-2',
        endpoint_url=None,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle,
    )
    return command._run_main(args, globals_)


@pytest.fixture
def auth_env(monkeypatch):
    # Set before deleting so monkeypatch restores the original absence even
    # though the command writes these variables itself.
    for name in (
        'AWS_BEARER_TOKEN_AGENT_REGISTRY',
        'AWS_AUTH_SCHEME_PREFERENCE',
    ):
        monkeypatch.setenv(name, 'placeholder')
        monkeypatch.delenv(name)


@pytest.fixture(autouse=True)
def endpoint():
    """The data plane endpoint, without building a client from the mock."""
    with patch.object(
        dataplane, 'resolve_data_plane_endpoint', return_value=ENDPOINT
    ) as resolve:
        yield resolve


SOURCE = {
    'registryId': REGISTRY_ID,
    'recordId': 'rec',
    'endpoint': ENDPOINT,
    'sha256': '0' * 64,
}


def _previous_install(folder, name='pdf-extract', marker=True, **source):
    """A skill installed earlier, from SOURCE unless told otherwise."""
    skill = os.path.join(str(folder), name)
    os.makedirs(skill)
    with open(os.path.join(skill, 'SKILL.md'), 'w') as f:
        f.write('old')
    if marker:
        with open(os.path.join(skill, PROVENANCE_MARKER), 'w') as f:
            json.dump(dict(SOURCE, **source), f)
    return skill


def _leftovers(target):
    return [n for n in os.listdir(target) if n.startswith('.')]


def test_install_succeeds_and_leaves_nothing_behind(tmp_path, capsys):
    command, client = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert _leftovers(tmp_path) == []
    # The URL comes from the record; there is no separate download call.
    assert command._download.call_args.args[0] == S3_URL
    client.get_registry_record_package_download_url.assert_not_called()
    err = capsys.readouterr().err
    assert f'Installed pdf-extract to {tmp_path / "pdf-extract"}' in err
    # The download line names the host only.
    assert 'from https://bucket.s3.us-west-2.amazonaws.com...' in err
    _assert_no_query(err)


def test_install_keeps_the_presigned_url_out_of_history(
    tmp_path, history_recorder
):
    collected = []
    history_recorder.add_handler(
        Mock(emit=lambda *event: collected.append(event))
    )
    history_recorder.enable()
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    # What botocore records for the BatchGet call.
    history_recorder.record(
        'PARSED_RESPONSE',
        {'registryRecords': [{'artifact': {'downloadUrl': S3_URL}}]},
    )
    recorded = repr(collected)
    for secret in ('ASIAEXAMPLE', 'IQoJsession', 'deadbeef'):
        assert secret not in recorded
    assert 'X-Amz-Signature=<redacted>' in recorded


@posix_only
def test_installed_script_stays_executable(tmp_path):
    archive = make_zip(
        [('SKILL.md', SKILL_MD), _with_mode('scripts/run.sh', 0o100755)]
    )
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert stat.S_IMODE(os.stat(skill / 'scripts' / 'run.sh').st_mode) == (
        0o755
    )
    assert os.access(skill / 'scripts' / 'run.sh', os.X_OK)
    assert stat.S_IMODE(os.stat(skill).st_mode) == 0o755


def test_digest_mismatch_refuses_and_keeps_existing_install(tmp_path):
    _previous_install(tmp_path)
    artifact = {'sha256': '0' * 64, 'downloadUrl': S3_URL}
    command, _ = _command({'name': 'pdf-extract', 'artifact': artifact})
    with pytest.raises(AgentRegistryJWTError, match='does not match'):
        _run(command, tmp_path, force=True)
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    assert _leftovers(tmp_path) == []


def test_digest_is_compared_in_constant_time(tmp_path):
    archive = make_zip({'SKILL.md': SKILL_MD})
    expected = hashlib.sha256(archive).hexdigest()
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    with patch.object(
        install_skill.hmac, 'compare_digest', wraps=hmac.compare_digest
    ) as compare:
        assert _run(command, tmp_path) == 0
    compare.assert_called_once_with(expected, expected)


@pytest.mark.parametrize(
    'artifact',
    [
        None,  # absent, as on a record without a package
        {},
        {'sha256': 'a' * 64},
        {'sha256': 'a' * 64, 'downloadUrl': ''},
        {'sha256': 'a' * 64, 'downloadUrl': None},
    ],
)
def test_record_without_downloadable_package_is_refused(tmp_path, artifact):
    command, client = _command({'name': 'pdf-extract'})
    response = client.batch_get_discoverable_registry_record.return_value
    record = response['registryRecords'][0]
    if artifact is None:
        del record['artifact']
    else:
        record['artifact'] = artifact
    with pytest.raises(AgentRegistryJWTError, match='no downloadable package'):
        _run(command, tmp_path)
    command._download.assert_not_called()
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    'digest',
    [
        'sha256:' + 'a' * 64,
        'A' * 64,
        'a' * 63,
        'a' * 65,
        'g' * 64,
        ' ' + 'a' * 63,
        'a' * 64 + '\n',
        '',
        None,
        123,
    ],
)
def test_malformed_digest_is_refused_before_download(tmp_path, digest):
    artifact = {'sha256': digest, 'downloadUrl': S3_URL}
    command, _ = _command({'name': 'pdf-extract', 'artifact': artifact})
    with pytest.raises(AgentRegistryJWTError, match='valid SHA-256'):
        _run(command, tmp_path)
    command._download.assert_not_called()


def test_install_trusts_the_configured_ca_bundle(tmp_path):
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, ca_bundle='/corp.pem') == 0
    assert command._download.call_args.args[2] == '/corp.pem'


def test_force_replaces_existing_install(tmp_path):
    _previous_install(tmp_path)
    (tmp_path / 'pdf-extract' / 'stale.txt').write_text('old')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 0
    assert not (tmp_path / 'pdf-extract' / 'stale.txt').exists()
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert _leftovers(tmp_path) == []


@pytest.mark.parametrize('force', [True, False])
def test_folder_without_skill_md_is_never_replaced(tmp_path, capsys, force):
    (tmp_path / 'pdf-extract').mkdir()
    (tmp_path / 'pdf-extract' / 'notes.txt').write_text('mine')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 1
    # The folder's name is SKILL.md's, so known after the download.
    command._download.assert_called_once()
    assert (tmp_path / 'pdf-extract' / 'notes.txt').read_text() == 'mine'
    assert 'not an installed skill' in capsys.readouterr().err


def test_file_in_the_way_is_never_replaced(tmp_path, capsys):
    (tmp_path / 'pdf-extract').write_text('a file')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    assert (tmp_path / 'pdf-extract').read_text() == 'a file'
    assert 'not an installed skill' in capsys.readouterr().err


def test_record_name_is_never_a_path(tmp_path):
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'keep.txt').write_text('important')
    target = tmp_path / 'skills'
    # The SKILL.md name is the folder; the record's name is only shown.
    archive = make_zip({'SKILL.md': make_skill_md('victim')})
    command, _ = _command({'name': '../victim'}, archive=archive)
    assert _run(command, target, force=True) == 0
    assert (victim / 'keep.txt').read_text() == 'important'
    assert sorted(os.listdir(victim)) == ['keep.txt']
    assert (target / 'victim' / 'SKILL.md').is_file()


@pytest.mark.parametrize('name', ['con', 'lpt1'])
def test_windows_device_skill_md_name_is_refused_on_windows(
    monkeypatch, tmp_path, name
):
    _on_windows(monkeypatch)
    archive = make_zip({'SKILL.md': make_skill_md(name)})
    command, _ = _command({'name': name}, archive=archive)
    with pytest.raises(AgentRegistryJWTError, match='device name'):
        _run(command, tmp_path)
    assert os.listdir(tmp_path) == []


@posix_only
@pytest.mark.parametrize('name', ['con', 'lpt1'])
def test_windows_device_skill_md_name_is_installed_elsewhere(
    monkeypatch, tmp_path, name
):
    _on_windows(monkeypatch, False)
    archive = make_zip({'SKILL.md': make_skill_md(name)})
    command, _ = _command({'name': name}, archive=archive)
    assert _run(command, tmp_path) == 0
    assert (tmp_path / name / 'SKILL.md').is_file()


def test_record_name_is_shown_safely(tmp_path, capsys):
    command, _ = _command({'name': 'Pdf\x1b[2J\u202e'})
    assert _run(command, tmp_path) == 0
    err = capsys.readouterr().err
    assert (
        "Record 'Pdf\\x1b[2J\\u202e' installs as skill 'pdf-extract'." in err
    )
    assert '\x1b' not in err
    assert '\u202e' not in err


@pytest.mark.parametrize('name', [None, '', 7, ['pdf-extract']])
def test_missing_or_non_string_record_name_still_installs(
    tmp_path, capsys, name
):
    record = {'recordId': 'abcdef123456'}
    if name is not None:
        record['name'] = name
    command, _ = _command(record)
    assert _run(command, tmp_path, record_id='abcdef123456') == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    err = capsys.readouterr().err
    assert 'Downloading abcdef123456 from https://' in err
    assert 'installs as skill' not in err


def test_symlinked_install_folder_is_not_replaced(tmp_path, capsys):
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / 'SKILL.md').write_text('keep')
    target = tmp_path / 'skills'
    target.mkdir()
    os.symlink(elsewhere, target / 'pdf-extract')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, target, force=True) == 1
    # The folder's name is SKILL.md's, so known after the download.
    command._download.assert_called_once()
    assert (elsewhere / 'SKILL.md').read_text() == 'keep'
    assert os.path.islink(target / 'pdf-extract')
    assert 'outside' in capsys.readouterr().err


@pytest.mark.parametrize(
    'url',
    [
        'https://evil.example/pkg.zip',
        'http://bucket.s3.us-west-2.amazonaws.com/x',
    ],
)
def test_non_s3_download_url_is_refused_before_download(tmp_path, url):
    command, _ = _command({'name': 'pdf-extract'}, url=url)
    with pytest.raises(AgentRegistryJWTError):
        _run(command, tmp_path)
    command._download.assert_not_called()


def test_archive_without_skill_md_is_refused(tmp_path):
    command, _ = _command(
        {'name': 'pdf-extract'}, archive=make_zip({'README': 'x'})
    )
    with pytest.raises(AgentRegistryJWTError, match='SKILL.md'):
        _run(command, tmp_path)
    assert not (tmp_path / 'pdf-extract').exists()
    assert _leftovers(tmp_path) == []


def test_unsafe_archive_is_refused_before_any_folder_is_touched(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command(
        {'name': 'pdf-extract'},
        archive=make_zip({'SKILL.md': 'x', '../escape': 'y'}),
        agent_configs=configs,
    )
    with pytest.raises(AgentRegistryJWTError, match='traversal'):
        _run(command, None)
    for folder in folders.values():
        assert not os.path.exists(folder)


def test_failed_swap_restores_previous_install(tmp_path, capsys):
    _previous_install(tmp_path)
    command, _ = _command({'name': 'pdf-extract'})
    real_rename = os.rename
    calls = []

    def flaky_rename(src, dst):
        calls.append((src, dst))
        if len(calls) == 2:  # moving the staged tree into place
            raise OSError('disk full')
        return real_rename(src, dst)

    with patch.object(install_skill.os, 'rename', side_effect=flaky_rename):
        assert _run(command, tmp_path, force=True) == 1
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    assert _leftovers(tmp_path) == []
    assert 'disk full' in capsys.readouterr().err


def test_failed_restore_keeps_the_error_and_says_where_the_backup_is(
    tmp_path, capsys
):
    _previous_install(tmp_path)
    command, _ = _command({'name': 'pdf-extract'})
    real_rename = os.rename
    calls = []

    def flaky_rename(src, dst):
        calls.append((src, dst))
        if len(calls) == 2:  # moving the staged tree into place
            raise OSError('disk full')
        if len(calls) == 3:  # putting the previous install back
            raise OSError('read-only file system')
        return real_rename(src, dst)

    with patch.object(install_skill.os, 'rename', side_effect=flaky_rename):
        assert _run(command, tmp_path, force=True) == 1
    backup = calls[0][1]
    assert os.path.basename(backup).startswith('.pdf-extract.old-')
    # The previous install is still there to move back by hand.
    assert open(os.path.join(backup, 'SKILL.md')).read() == 'old'
    err = capsys.readouterr().err
    assert (
        f'Warning: could not restore the previous install to '
        f'{tmp_path / "pdf-extract"} (read-only file system). It is in '
        f'{backup}.'
    ) in err
    # The swap's own error is the one reported for the folder.
    assert 'Could not install pdf-extract' in err
    assert 'disk full' in err


def _rmtree_failing_for(prefix):
    real_rmtree = install_skill.shutil.rmtree

    def rmtree(path, *args, **kwargs):
        if os.path.basename(path).startswith(prefix):
            raise PermissionError('denied')
        return real_rmtree(path, *args, **kwargs)

    return patch.object(install_skill.shutil, 'rmtree', side_effect=rmtree)


def test_backup_that_cannot_be_removed_is_reported(tmp_path, capsys):
    _previous_install(tmp_path)
    command, _ = _command({'name': 'pdf-extract'})
    with _rmtree_failing_for('.pdf-extract.old-'):
        assert _run(command, tmp_path, force=True) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    [backup] = _leftovers(tmp_path)
    assert backup.startswith('.pdf-extract.old-')
    err = capsys.readouterr().err
    assert f'Warning: could not remove {tmp_path / backup}' in err
    assert 'denied' in err


def test_staging_folder_that_cannot_be_removed_is_reported(tmp_path, capsys):
    command, _ = _command({'name': 'pdf-extract'})
    with (
        patch.object(
            install_skill,
            '_safe_extract',
            side_effect=AgentRegistryJWTError('bad entry'),
        ),
        _rmtree_failing_for('.pdf-extract.staging-'),
    ):
        assert _run(command, tmp_path) == 1
    [staged] = _leftovers(tmp_path)
    assert staged.startswith('.pdf-extract.staging-')
    err = capsys.readouterr().err
    assert 'bad entry' in err
    assert f'Warning: could not remove {tmp_path / staged}' in err


# --- BatchGet response ------------------------------------------------------


def test_the_requested_record_is_picked_from_the_response(tmp_path):
    command, client = _command({'name': 'pdf-extract'})
    response = client.batch_get_discoverable_registry_record.return_value
    response['registryRecords'].insert(
        0,
        {
            'recordId': 'other',
            'name': 'other-skill',
            'artifact': {'sha256': '0' * 64, 'downloadUrl': S3_URL},
        },
    )
    assert _run(command, tmp_path) == 0
    assert os.listdir(tmp_path) == ['pdf-extract']


def test_a_response_with_only_another_record_is_refused(tmp_path):
    command, client = _command({'name': 'other-skill', 'recordId': 'other'})
    with pytest.raises(AgentRegistryJWTError, match='other than rec'):
        _run(command, tmp_path)
    command._download.assert_not_called()
    assert os.listdir(tmp_path) == []


def test_a_record_arn_matches_its_record_id(tmp_path):
    arn = f'{REGISTRY_ARN}/record/rec'
    command, client = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, record_id=arn) == 0
    entries = client.batch_get_discoverable_registry_record.call_args.kwargs[
        'entries'
    ]
    assert entries == [{'registryId': REGISTRY_ID, 'recordIds': [arn]}]


def test_batch_get_errors_are_shown(tmp_path):
    command, client = _command({'name': 'pdf-extract'})
    client.batch_get_discoverable_registry_record.return_value = {
        'registryRecords': [],
        'errors': [
            {
                'registryId': REGISTRY_ID,
                'recordId': 'rec',
                'errorCode': 'AccessDenied',
                'message': 'Not entitled\x1b[2J to this record',
            }
        ],
    }
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    message = str(e.value)
    assert 'AccessDenied' in message
    assert 'Not entitled' in message
    assert 'not found' not in message
    assert '\x1b' not in message


def test_empty_response_is_reported_as_not_found(tmp_path):
    command, client = _command({'name': 'pdf-extract'})
    client.batch_get_discoverable_registry_record.return_value = {
        'registryRecords': [],
        'errors': [],
    }
    with pytest.raises(AgentRegistryJWTError, match='not found'):
        _run(command, tmp_path)


# --- Provenance marker ------------------------------------------------------


def _marker(skill):
    with open(os.path.join(str(skill), PROVENANCE_MARKER)) as f:
        return json.load(f)


def _digest(archive=None):
    archive = SKILL_ARCHIVE if archive is None else archive
    return hashlib.sha256(archive).hexdigest()


def test_marker_records_where_the_skill_came_from(tmp_path, endpoint):
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    assert _marker(tmp_path / 'pdf-extract') == {
        'registryId': REGISTRY_ID,
        'recordId': 'rec',
        'endpoint': ENDPOINT,
        'sha256': _digest(),
        'content': 'package',
    }
    # A SigV4 call may go to a plain-http local endpoint.
    assert endpoint.call_args.kwargs == {'https_only': False}


@posix_only
def test_marker_is_0644_whatever_the_umask(tmp_path):
    previous = os.umask(0o077)
    try:
        command, _ = _command({'name': 'pdf-extract'})
        assert _run(command, tmp_path) == 0
    finally:
        os.umask(previous)
    marker = tmp_path / 'pdf-extract' / PROVENANCE_MARKER
    assert stat.S_IMODE(os.stat(marker).st_mode) == 0o644


def test_marker_holds_bare_ids_for_arns(tmp_path):
    record_arn = f'{REGISTRY_ARN}/record/rec'
    command, _ = _command({'name': 'pdf-extract'})
    assert (
        _run(command, tmp_path, registry_id=REGISTRY_ARN, record_id=record_arn)
        == 0
    )
    marker = _marker(tmp_path / 'pdf-extract')
    assert marker['registryId'] == REGISTRY_ID
    assert marker['recordId'] == 'rec'


def test_marker_is_written_for_every_agent_folder(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None) == 0
    for agent in ('claude-code', 'codex'):
        skill = os.path.join(folders[agent], 'pdf-extract')
        assert _marker(skill)['registryId'] == REGISTRY_ID


def test_marker_lands_with_the_install_in_one_rename(tmp_path):
    command, _ = _command({'name': 'pdf-extract'})
    real_replace = install_skill._replace
    staged = []

    def replace(source, destination):
        staged.append(os.listdir(source))
        return real_replace(source, destination)

    with patch.object(install_skill, '_replace', side_effect=replace):
        assert _run(command, tmp_path) == 0
    assert PROVENANCE_MARKER in staged[0]


@pytest.mark.parametrize(
    'name',
    [
        PROVENANCE_MARKER,
        f'lib/{PROVENANCE_MARKER}',
        f'deep/er/{PROVENANCE_MARKER}',
        '.AGENT-REGISTRY-SKILL.JSON',
        'lib/.Agent-Registry-Skill.Json',
        f'{PROVENANCE_MARKER}/x.md',
        f'{PROVENANCE_MARKER}/',
    ],
)
def test_archive_cannot_bring_its_own_marker(tmp_path, name):
    archive = make_zip({'SKILL.md': SKILL_MD, name: '{}'})
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert (
        f'the name {PROVENANCE_MARKER} is reserved for the file in which '
        'install-skill notes where a skill came from'
    ) in str(e.value)
    # Refused before anything was written.
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    'name',
    [
        SKILL_METADATA_FILENAME,
        f'lib/{SKILL_METADATA_FILENAME}',
        f'deep/er/{SKILL_METADATA_FILENAME}',
        '.AWS-SKILL-METADATA',
        'lib/.Aws-Skill-Metadata',
        f'{SKILL_METADATA_FILENAME}/x.md',
        f'{SKILL_METADATA_FILENAME}/',
    ],
)
def test_archive_cannot_bring_agent_toolkit_metadata(tmp_path, name):
    # agent-toolkit would take the folder for a skill it installed.
    archive = make_zip({'SKILL.md': SKILL_MD, name: '{"version": "1"}'})
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert (
        f"the name {SKILL_METADATA_FILENAME} is reserved for agent-toolkit's "
        'install metadata'
    ) in str(e.value)
    assert os.listdir(tmp_path) == []


def test_force_replaces_a_skill_from_the_same_source(tmp_path):
    # The same endpoint, written another way.
    _previous_install(
        tmp_path, endpoint='https://Agent-Registry.us-west-2.api.aws:443/'
    )
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert _marker(tmp_path / 'pdf-extract') == dict(
        SOURCE, sha256=_digest(), content='package'
    )


@pytest.mark.parametrize(
    'installed,expected',
    [
        (
            {'registryId': 'otherREG123456'},
            'it was installed from registry otherREG123456, record rec, not '
            f'registry {REGISTRY_ID}, record rec.',
        ),
        (
            {'recordId': 'otherrec'},
            f'it was installed from registry {REGISTRY_ID}, record otherrec, '
            f'not registry {REGISTRY_ID}, record rec.',
        ),
        (
            {'endpoint': 'https://agent-registry.eu-west-1.api.aws'},
            f'it was installed from registry {REGISTRY_ID}, record rec at '
            f'https://agent-registry.eu-west-1.api.aws, not registry '
            f'{REGISTRY_ID}, record rec at {ENDPOINT}.',
        ),
    ],
)
@pytest.mark.parametrize('force', [True, False])
def test_skill_from_another_source_is_never_replaced(
    tmp_path, capsys, installed, expected, force
):
    _previous_install(tmp_path, **installed)
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 1
    # The folder's name is SKILL.md's, so known after the download.
    command._download.assert_called_once()
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    err = capsys.readouterr().err
    assert f'Refusing to replace {tmp_path / "pdf-extract"}: {expected}' in err
    assert (
        'Uninstall it first with aws agent-registry uninstall-skill --name '
        f'pdf-extract --target-directory {tmp_path}, or install into '
        'another folder with --agent or --target-directory.'
    ) in err
    assert 'Pass --force' not in err


@pytest.mark.parametrize('force', [True, False])
def test_skill_of_unknown_source_is_never_replaced(tmp_path, capsys, force):
    _previous_install(tmp_path, marker=False)
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 1
    # The folder's name is SKILL.md's, so known after the download.
    command._download.assert_called_once()
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    err = capsys.readouterr().err
    assert (
        f'Refusing to replace {tmp_path / "pdf-extract"}: it has no readable '
        f"{PROVENANCE_MARKER}, so this command can't tell where it came "
        'from. Move or delete the folder yourself, or install into another '
        'folder with --agent or --target-directory.'
    ) in err
    # uninstall-skill skips a folder without a marker, so it is not offered.
    assert 'uninstall-skill' not in err
    # It may have come from this command, with a damaged marker.
    assert "wasn't installed" not in err


def _write_marker(skill, content):
    path = os.path.join(skill, PROVENANCE_MARKER)
    with open(path, 'wb') as f:
        f.write(content if isinstance(content, bytes) else content.encode())


@pytest.mark.parametrize(
    'content',
    [
        b'not json',
        b'',
        b'[]',
        b'"text"',
        b'\xff\xfe\x00garbage',
        json.dumps(dict(SOURCE, registryId=1)),
        json.dumps(dict(SOURCE, endpoint=None)),
        json.dumps(dict(SOURCE, recordId=['rec'])),
        json.dumps({k: v for k, v in SOURCE.items() if k != 'sha256'}),
        # Valid but oversized.
        json.dumps(dict(SOURCE, padding='x' * 70_000)),
        # Deep enough to exhaust the JSON parser's recursion.
        '[' * 60_000,
    ],
)
def test_unreadable_marker_counts_as_unknown(tmp_path, content):
    skill = _previous_install(tmp_path, marker=False)
    _write_marker(skill, content)
    assert install_skill.read_provenance(skill) is None
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'


def test_symlinked_marker_counts_as_unknown(tmp_path):
    elsewhere = tmp_path / 'elsewhere.json'
    elsewhere.write_text(json.dumps(SOURCE))
    target = tmp_path / 'skills'
    skill = _previous_install(target, marker=False)
    os.symlink(elsewhere, os.path.join(skill, PROVENANCE_MARKER))
    assert install_skill.read_provenance(skill) is None
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, target, force=True) == 1
    assert (target / 'pdf-extract' / 'SKILL.md').read_text() == 'old'


def test_marker_that_is_a_folder_counts_as_unknown(tmp_path):
    skill = _previous_install(tmp_path, marker=False)
    os.mkdir(os.path.join(skill, PROVENANCE_MARKER))
    assert install_skill.read_provenance(skill) is None


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX FIFOs')
def test_marker_that_is_a_fifo_is_not_read(tmp_path):
    # Opening a FIFO for reading would block until a writer appears.
    skill = _previous_install(tmp_path, marker=False)
    os.mkfifo(os.path.join(skill, PROVENANCE_MARKER))
    assert install_skill.read_provenance(skill) is None


def test_missing_skill_folder_has_no_provenance(tmp_path):
    assert install_skill.read_provenance(str(tmp_path / 'absent')) is None


def test_marker_values_are_printed_safely(tmp_path, capsys):
    _previous_install(tmp_path, registryId='evil\x1b[2J\x07' + 'x' * 1000)
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    err = capsys.readouterr().err
    assert '\x1b' not in err and '\x07' not in err
    assert len(err) < 1200


def test_mixed_folders_replace_the_match_and_refuse_the_other(
    tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _previous_install(folders['claude-code'])
    shared = _previous_install(folders['codex'], registryId='otherREG123456')
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None, force=True) == 1
    assert open(os.path.join(claude, 'SKILL.md')).read() == SKILL_MD
    assert open(os.path.join(shared, 'SKILL.md')).read() == 'old'
    assert _marker(shared)['registryId'] == 'otherREG123456'
    err = capsys.readouterr().err
    assert 'Claude Code: Updated pdf-extract' in err
    assert 'Codex: Refusing to replace' in err
    # The advice names the agent whose folder it is.
    assert (
        'Uninstall it first with aws agent-registry uninstall-skill --name '
        'pdf-extract --agent codex, or install'
    ) in err


def test_endpoint_comparison_is_the_one_sign_out_uses():
    from awscli.customizations.agentregistry import sign_out, utils

    assert install_skill.comparable_endpoint is utils.comparable_endpoint
    assert sign_out.comparable_endpoint is utils.comparable_endpoint


@pytest.mark.parametrize(
    'first,second,same',
    [
        (ENDPOINT, ENDPOINT + '/', True),
        (ENDPOINT, 'HTTPS://Agent-Registry.US-WEST-2.api.aws:443', True),
        ('http://localhost:8080', 'http://LOCALHOST:8080/', True),
        ('http://localhost', 'http://localhost:80', True),
        (ENDPOINT, ENDPOINT + ':8443', False),
        (ENDPOINT, ENDPOINT + '/prefix', False),
        (ENDPOINT, ENDPOINT.replace('https', 'http'), False),
    ],
)
def test_comparable_endpoint(first, second, same):
    from awscli.customizations.agentregistry.utils import comparable_endpoint

    assert (comparable_endpoint(first) == comparable_endpoint(second)) is same


def test_uninstall_advice_names_the_agent(tmp_path, capsys):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _previous_install(folders['claude-code'], registryId='otherREG123456')
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None, force=True) == 1
    assert (
        'Uninstall it first with aws agent-registry uninstall-skill --name '
        'pdf-extract --agent claude-code, or install into another folder'
    ) in capsys.readouterr().err


def test_uninstall_advice_for_an_agent_is_its_uninstall_skill_command():
    command = install_skill._uninstall_command(
        'pdf-extract', '/x', 'claude-code'
    )
    assert command == (
        'aws agent-registry uninstall-skill --name pdf-extract '
        '--agent claude-code'
    )


@pytest.mark.parametrize(
    'folder,expected',
    [
        ('/home/me/skills', '/home/me/skills'),
        ('/home/me/my skills', "'/home/me/my skills'"),
        ("/home/me/it's", "'/home/me/it'\"'\"'s'"),
        ('/home/me/$HOME;rm', "'/home/me/$HOME;rm'"),
    ],
)
def test_uninstall_advice_quotes_the_folder(folder, expected):
    command = install_skill._uninstall_command('pdf-extract', folder, None)
    assert command == (
        'aws agent-registry uninstall-skill --name pdf-extract '
        f'--target-directory {expected}'
    )


def test_uninstall_advice_for_a_target_directory_with_a_space(
    tmp_path, capsys
):
    target = tmp_path / 'my skills'
    _previous_install(target, registryId='otherREG123456')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, target, force=True) == 1
    assert (
        'uninstall-skill --name pdf-extract --target-directory '
        f"'{target}', or install"
    ) in capsys.readouterr().err


@pytest.mark.parametrize('has_record_id', [True, False])
def test_nameless_record_requested_by_arn_installs(tmp_path, has_record_id):
    record_arn = f'{REGISTRY_ARN}/record/abcdef123456'
    record = {'recordArn': record_arn}
    if has_record_id:
        record['recordId'] = 'abcdef123456'
    command, client = _command(record)
    if not has_record_id:
        response = client.batch_get_discoverable_registry_record.return_value
        del response['registryRecords'][0]['recordId']
    assert _run(command, tmp_path, record_id=record_arn) == 0
    assert _marker(tmp_path / 'pdf-extract')['recordId'] == 'abcdef123456'


def test_record_id_comes_from_the_arn_when_the_record_has_none(tmp_path):
    record_arn = f'{REGISTRY_ARN}/record/rec'
    command, client = _command(
        {'name': 'pdf-extract', 'recordArn': record_arn}
    )
    response = client.batch_get_discoverable_registry_record.return_value
    del response['registryRecords'][0]['recordId']
    assert _run(command, tmp_path, record_id=record_arn) == 0
    assert _marker(tmp_path / 'pdf-extract')['recordId'] == 'rec'


@pytest.mark.parametrize(
    'record,requested,expected',
    [
        ({'recordId': 'rec'}, 'rec', 'rec'),
        ({'recordId': 'rec'}, f'{REGISTRY_ARN}/record/rec', 'rec'),
        ({}, f'{REGISTRY_ARN}/record/rec', 'rec'),
        ({'recordId': ''}, f'{REGISTRY_ARN}/record/rec', 'rec'),
        ({'recordId': 7}, 'rec', 'rec'),
        ({}, 'rec', 'rec'),
    ],
)
def test_record_id(record, requested, expected):
    assert install_skill._record_id(record, requested) == expected


def _change_during_extraction(change):
    """Run ``change(destination)`` while the archive is being extracted."""
    real_extract = install_skill._safe_extract

    def extract(archive, staged):
        real_extract(archive, staged)
        change(os.path.join(os.path.dirname(staged), 'pdf-extract'))

    return patch.object(install_skill, '_safe_extract', side_effect=extract)


@pytest.mark.parametrize('force', [True, False])
def test_skill_put_in_place_by_another_source_meanwhile_is_kept(
    tmp_path, capsys, force
):
    # Another run, from another registry, wins the race to the folder.
    def other_run(destination):
        _previous_install(
            os.path.dirname(destination), registryId='otherREG123456'
        )

    command, _ = _command({'name': 'pdf-extract'})
    with _change_during_extraction(other_run):
        assert _run(command, tmp_path, force=force) == 1
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'SKILL.md').read_text() == 'old'
    assert _marker(skill)['registryId'] == 'otherREG123456'
    # The staged copy is cleaned up.
    assert _leftovers(tmp_path) == []
    err = capsys.readouterr().err
    assert (
        f'Refusing to replace {skill}: it was installed from registry '
        f'otherREG123456, record rec, not registry {REGISTRY_ID}, record rec.'
    ) in err
    assert 'Could not install' not in err


def test_folder_replaced_by_a_link_meanwhile_is_kept(tmp_path, capsys):
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    target = tmp_path / 'skills'

    def link(destination):
        os.symlink(elsewhere, destination)

    command, _ = _command({'name': 'pdf-extract'})
    with _change_during_extraction(link):
        assert _run(command, target) == 1
    assert os.path.islink(target / 'pdf-extract')
    assert os.listdir(elsewhere) == []
    assert _leftovers(target) == []
    assert 'it is a symbolic link' in capsys.readouterr().err


def test_same_source_installed_meanwhile_is_replaced_with_force(tmp_path):
    def same_run(destination):
        _previous_install(os.path.dirname(destination))

    command, _ = _command({'name': 'pdf-extract'})
    with _change_during_extraction(same_run):
        assert _run(command, tmp_path, force=True) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert _leftovers(tmp_path) == []


def test_sources_are_described_in_one_format():
    marker = dict(SOURCE)
    detail = install_skill.source_detail(marker)
    assert detail == f'registry {REGISTRY_ID}, record rec'
    assert install_skill.describe_source(marker) == f'from {detail}'
    assert install_skill.source_detail(marker, with_endpoint=True) == (
        f'{detail} at {ENDPOINT}'
    )


def test_force_help_says_what_it_replaces():
    [force] = [
        arg for arg in InstallSkillCommand.ARG_TABLE if arg['name'] == 'force'
    ]
    assert force['help_text'] == (
        'Reinstall even if the installed copy is already up to date, and '
        "replace a copy of the record's package with its "
        '<code>SKILL.md</code> text when the record offers only the text. A '
        'skill installed from another registry, endpoint or record, or by '
        'anything other than this command, is never replaced.'
    )
    description = InstallSkillCommand.DESCRIPTION
    assert 'updates a skill it installed' in description
    assert (
        "A skill installed from the record's package is kept, though, when "
        'the record offers only its ``SKILL.md`` text, because the registry '
        'can leave the package out; pass ``--force`` to replace it with the '
        'text alone.'
    ) in description
    assert 'one a newer version of the AWS CLI installed' in description


def test_help_states_the_naming_rule():
    description = InstallSkillCommand.DESCRIPTION
    assert (
        'the command installs the skill in a folder named after the '
        "``name`` in the frontmatter of the package's ``SKILL.md``, whatever "
        'the record is named, and says so when the two names differ.'
    ) in description
    assert (
        'A valid skill name (at most 64 lowercase letters, digits and '
        'hyphens, with no hyphen at the start or end and no two hyphens in a '
        'row) is installed as it is.'
    ) in description
    assert 'is installed with a warning' in description
    assert 'the earlier install is reported, not removed' in description
    assert 'named after the record' not in description
    # Nothing says the record's name must match the skill's.
    assert 'must match' not in description
    assert "record's name" not in description
    [target] = [
        arg
        for arg in InstallSkillCommand.ARG_TABLE
        if arg['name'] == 'target-directory'
    ]
    assert (
        "subdirectory named after the skill's name in its "
        '<code>SKILL.md</code>'
    ) in target['help_text']
    assert 'record' not in target['help_text']


def test_help_describes_the_skill_md_fallback():
    description = InstallSkillCommand.DESCRIPTION
    assert (
        'A record with no downloadable package that holds the text of its '
        '``SKILL.md`` is installed from that text, as it is: only '
        '``SKILL.md`` is installed, nothing is downloaded, and the command '
        'says so. A ``SKILL.md`` the record only links to is never fetched, '
        'so such a record is refused, as is a record with neither.'
    ) in description
    assert 'refused if the record has no downloadable package' not in (
        description
    )
    assert 'whether it holds the package or only ``SKILL.md``' in description


# --- Install or update ------------------------------------------------------


@pytest.mark.parametrize('force', [False, True])
def test_missing_folder_is_installed(tmp_path, capsys, force):
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert (
        f'Installed pdf-extract to {tmp_path / "pdf-extract"}'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('force', [False, True])
def test_symlinked_folder_is_refused(tmp_path, capsys, force):
    target = tmp_path / 'skills'
    target.mkdir()
    os.symlink(tmp_path, target / 'pdf-extract')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, target, force=force) == 1
    # The folder's name is SKILL.md's, so known after the download.
    command._download.assert_called_once()
    assert os.path.islink(target / 'pdf-extract')


def test_up_to_date_skill_is_left_alone(tmp_path, capsys):
    skill = _previous_install(tmp_path, sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    command._download.assert_not_called()
    assert open(os.path.join(skill, 'SKILL.md')).read() == 'old'
    assert capsys.readouterr().err.strip() == (
        f'pdf-extract is already up to date at {skill}.'
    )


def test_force_reinstalls_an_up_to_date_skill(tmp_path, capsys):
    skill = _previous_install(tmp_path, sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 0
    command._download.assert_called_once()
    assert open(os.path.join(skill, 'SKILL.md')).read() == SKILL_MD
    assert f'Reinstalled pdf-extract at {skill}.' in capsys.readouterr().err


@pytest.mark.parametrize('force', [False, True])
def test_skill_from_the_same_source_is_updated(tmp_path, capsys, force):
    skill = _previous_install(tmp_path, sha256='a' * 64)
    (pathlib.Path(skill) / 'edited.txt').write_text('local edit')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 0
    assert open(os.path.join(skill, 'SKILL.md')).read() == SKILL_MD
    # No check for local edits: the update replaces the folder.
    assert not os.path.exists(os.path.join(skill, 'edited.txt'))
    assert _marker(skill)['sha256'] == _digest()
    assert (
        f'Updated pdf-extract at {skill} (aaaaaaaaaaaa\u2026 \u2192 '
        f'{_digest()[:12]}\u2026).'
    ) in capsys.readouterr().err


def test_up_to_date_by_the_time_of_the_swap_counts_as_success(
    tmp_path, capsys
):
    # Another run installed the same package while this one was extracting.
    def same_package(destination):
        _previous_install(os.path.dirname(destination), sha256=_digest())

    command, _ = _command({'name': 'pdf-extract'})
    with _change_during_extraction(same_package):
        assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    # Left as the other run put it, and the staged copy is gone.
    assert (skill / 'SKILL.md').read_text() == 'old'
    assert _leftovers(tmp_path) == []
    assert f'pdf-extract is already up to date at {skill}.' in (
        capsys.readouterr().err
    )


@pytest.mark.parametrize(
    'claude,codex,expected',
    [
        ('up to date', 'missing', 0),
        ('up to date', 'stale', 0),
        ('up to date', 'other source', 1),
        ('stale', 'no marker', 1),
        ('missing', 'other source', 1),
    ],
)
def test_exit_code_across_folders(tmp_path, claude, codex, expected):
    configs, folders = make_agents(str(tmp_path / 'home'))
    states = {
        'up to date': {'sha256': _digest()},
        'stale': {'sha256': 'a' * 64},
        'other source': {'registryId': 'otherREG123456'},
    }
    for agent, state in (('claude-code', claude), ('codex', codex)):
        if state == 'no marker':
            _previous_install(folders[agent], marker=False)
        elif state != 'missing':
            _previous_install(folders[agent], **states[state])
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None) == expected


def test_a_failed_install_makes_the_exit_code_1(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _previous_install(folders['claude-code'], sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    with patch.object(
        install_skill, '_safe_extract', side_effect=OSError('disk full')
    ):
        assert _run(command, None) == 1


# --- Package layouts --------------------------------------------------------


def _files(folder):
    return sorted(
        os.path.relpath(os.path.join(root, name), folder)
        for root, _, names in os.walk(folder)
        for name in names
    )


def test_skill_in_a_single_top_level_folder_is_installed_without_it(
    tmp_path,
):
    out = _extract(
        tmp_path,
        make_zip(
            [
                (zipfile.ZipInfo('my-skill/'), ''),
                ('my-skill/SKILL.md', 'x'),
                ('my-skill/lib/a.py', 'y'),
            ]
        ),
    )
    assert _files(out) == ['SKILL.md', os.path.join('lib', 'a.py')]
    assert (out / 'lib' / 'a.py').read_text() == 'y'


def test_wrapped_skill_installs_under_the_skill_md_name(tmp_path):
    # Neither the wrapper's name nor the record's matters.
    wrapped = make_skill_md(body='wrapped')
    archive = make_zip({'other-name/SKILL.md': wrapped})
    command, _ = _command({'name': 'PDF_Extract'}, archive=archive)
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == wrapped
    assert not (tmp_path / 'pdf-extract' / 'other-name').exists()
    assert not (tmp_path / 'other-name').exists()


# --- Installed under the SKILL.md name --------------------------------------


def _archive_named(name, body='skill'):
    return make_zip({'SKILL.md': make_skill_md(name, body=body)})


def test_package_installs_under_the_skill_md_name(tmp_path, capsys):
    archive = _archive_named('pdf-processing-skill')
    command, _ = _command({'name': 'pdf_processing_skill'}, archive=archive)
    assert _run(command, tmp_path) == 0
    assert sorted(os.listdir(tmp_path)) == ['pdf-processing-skill']
    skill = tmp_path / 'pdf-processing-skill'
    assert (skill / 'SKILL.md').is_file()
    assert _marker(str(skill))['recordId'] == 'rec'
    err = capsys.readouterr().err
    # The download line names the record, the result line the folder.
    assert 'Downloading pdf_processing_skill from https://' in err
    assert f'Installed pdf-processing-skill to {skill}' in err
    assert 'Warning' not in err


def test_record_name_is_not_required_to_match_skill_md_name(tmp_path, capsys):
    archive = _archive_named('pdf-processing-skill')
    command, _ = _command({'name': 'pdf_processing_skill'}, archive=archive)
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'pdf-processing-skill' / 'SKILL.md').is_file()
    lines = capsys.readouterr().err.splitlines()
    info = (
        "Record 'pdf_processing_skill' installs as skill "
        "'pdf-processing-skill'."
    )
    assert lines.count(info) == 1


@pytest.mark.parametrize(
    'record_name',
    ['totally-different', 'Team/PDF Tools v2', 'x' * 255, '../victim', '_'],
)
def test_other_record_name_installs_under_skill_md_name_with_info_line(
    tmp_path, capsys, record_name
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': record_name}, agent_configs=configs)
    assert _run(command, None) == 0
    for agent in ('claude-code', 'codex'):
        skill = os.path.join(folders[agent], 'pdf-extract')
        assert open(os.path.join(skill, 'SKILL.md')).read() == SKILL_MD
    err = capsys.readouterr().err
    # Once, however many folders it goes into, and not as a warning.
    assert err.count('installs as skill') == 1
    assert (
        f"Record {install_skill.printable(repr(record_name))} installs as "
        "skill 'pdf-extract'."
    ) in err
    assert 'Warning' not in err


def test_same_names_print_no_info_line(tmp_path, capsys):
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    err = capsys.readouterr().err
    assert 'installs as skill' not in err
    assert 'Warning' not in err
    assert 'Downloading pdf-extract from https://' in err


@pytest.mark.parametrize('record_name', ['PDF-Extract', 'pdf_extract'])
def test_names_that_differ_only_in_form_still_print_the_info_line(
    tmp_path, capsys, record_name
):
    command, _ = _command({'name': record_name})
    assert _run(command, tmp_path) == 0
    assert (
        f"Record {record_name!r} installs as skill 'pdf-extract'."
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('name', ['PDF_Extract', 'pdf_extract', 'Pdf.Extract'])
def test_legacy_skill_md_name_installs_with_one_warning(
    tmp_path, capsys, name
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    archive = _archive_named(name)
    command, _ = _command(
        {'name': 'pdf-extract'}, archive=archive, agent_configs=configs
    )
    assert _run(command, None) == 0
    for agent in ('claude-code', 'codex'):
        skill = os.path.join(folders[agent], name)
        # SKILL.md is installed as published, never rewritten.
        with open(os.path.join(skill, 'SKILL.md')) as f:
            assert f.read() == make_skill_md(name)
    err = capsys.readouterr().err
    warning = (
        f'Warning: {name} is not an Agent Skills name (at most 64 lowercase '
        'letters, digits and hyphens, with no hyphen at the start or end and '
        'no two hyphens in a row); some agents may not load it.'
    )
    # Once, however many folders it goes into.
    assert err.count('Warning') == 1
    assert warning in err.splitlines()


@pytest.mark.parametrize(
    'name', ['pdf/extract', '.pdf-extract', 'p' * 65, 'pdf extract', '-pdf']
)
def test_unsafe_skill_md_name_is_refused_with_publisher_advice(
    tmp_path, capsys, name
):
    archive = make_zip({'SKILL.md': f'---\nname: "{name}"\n---\n'})
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert os.listdir(tmp_path) == []
    message = str(e.value)
    assert message.startswith(
        'Refusing to install pdf-extract: its SKILL.md names the skill '
        f"{name!r}, which cannot name its folder: a skill's folder name must "
        'be a skill name under the Agent Skills specification'
    )
    assert message.endswith(
        'The publisher must rename the skill in its SKILL.md.'
    )
    assert 'Warning' not in capsys.readouterr().err


@pytest.mark.parametrize('folder', ['pdf-extract', 'PDF_Extract', 'other'])
def test_up_to_date_copy_is_found_by_marker_without_download(
    tmp_path, capsys, folder
):
    skill = _previous_install(tmp_path, name=folder, sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    command._download.assert_not_called()
    assert sorted(os.listdir(tmp_path)) == [folder]
    assert open(os.path.join(skill, 'SKILL.md')).read() == 'old'
    assert capsys.readouterr().err.strip() == (
        f'{folder} is already up to date at '
        f'{os.path.join(os.path.realpath(tmp_path), folder)}.'
    )


@pytest.mark.parametrize('folder', ['pdf-extract', 'PDF_Extract'])
def test_force_reinstalls_the_up_to_date_copy(tmp_path, capsys, folder):
    _previous_install(tmp_path, name=folder, sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 0
    command._download.assert_called_once()
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'SKILL.md').read_text() == SKILL_MD
    err = capsys.readouterr().err
    if folder == 'pdf-extract':
        assert f'Reinstalled pdf-extract at {skill}.' in err
        assert 'earlier install' not in err
    else:
        # Under the SKILL.md name; the copy under the other name is kept.
        assert f'Installed pdf-extract to {skill}' in err
        assert (tmp_path / folder / 'SKILL.md').read_text() == 'old'
        assert 'An earlier install of this record is at' in err


def test_earlier_install_under_another_name_is_reported_not_deleted(
    tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    old = _previous_install(
        folders['claude-code'], name='pdf_extract', sha256='a' * 64
    )
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None) == 0
    assert open(os.path.join(old, 'SKILL.md')).read() == 'old'
    assert _marker(old)['sha256'] == 'a' * 64
    new = os.path.join(folders['claude-code'], 'pdf-extract')
    assert open(os.path.join(new, 'SKILL.md')).read() == SKILL_MD
    err = capsys.readouterr().err
    old_path = os.path.join(
        os.path.realpath(folders['claude-code']), 'pdf_extract'
    )
    assert (
        f'Claude Code: An earlier install of this record is at {old_path}; '
        'uninstall it with aws agent-registry uninstall-skill --name '
        'pdf_extract --agent claude-code if you no longer need it.'
    ) in err
    # Codex had no earlier install.
    assert err.count('earlier install') == 1


def _earlier(path, name, folder):
    return (
        f'An earlier install of this record is at {path}; uninstall it with '
        f'aws agent-registry uninstall-skill --name {name} '
        f'--target-directory {folder} if you no longer need it.'
    )


def test_other_copies_are_reported_when_the_folder_is_left_as_is(
    tmp_path, capsys
):
    _previous_install(tmp_path, name='pdf-extract', sha256=_digest())
    older = _previous_install(tmp_path, name='pdf_extract', sha256='a' * 64)
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    command._download.assert_not_called()
    assert sorted(os.listdir(tmp_path)) == ['pdf-extract', 'pdf_extract']
    assert open(os.path.join(older, 'SKILL.md')).read() == 'old'
    assert _marker(older)['sha256'] == 'a' * 64
    real = os.path.realpath(tmp_path)
    assert capsys.readouterr().err.strip().splitlines() == [
        f'pdf-extract is already up to date at '
        f'{os.path.join(real, "pdf-extract")}.',
        _earlier(os.path.join(real, 'pdf_extract'), 'pdf_extract', tmp_path),
    ]


def test_earlier_install_is_not_reported_when_it_was_replaced(
    tmp_path, capsys
):
    _previous_install(tmp_path, sha256='a' * 64)
    command, _ = _command({'name': 'pdf_extract'})
    assert _run(command, tmp_path) == 0
    err = capsys.readouterr().err
    assert 'Updated pdf-extract' in err
    assert 'earlier install' not in err


def test_an_earlier_install_does_not_make_an_occupied_folder_replaceable(
    tmp_path, capsys
):
    # The SKILL.md name's folder holds someone else's skill.
    _previous_install(tmp_path, name='pdf_extract', sha256='a' * 64)
    _previous_install(tmp_path, registryId='otherREG123456')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    assert (tmp_path / 'pdf_extract' / 'SKILL.md').read_text() == 'old'
    err = capsys.readouterr().err
    assert 'Refusing to replace' in err
    assert 'earlier install' not in err


@pytest.mark.parametrize(
    'name', ['claude-helper', 'anthropic-tools', 'claude', 'anthropic']
)
def test_reserved_words_are_not_checked(tmp_path, name):
    command, _ = _command({'name': name}, archive=_archive_named(name))
    assert _run(command, tmp_path) == 0
    assert (tmp_path / name / 'SKILL.md').is_file()


@pytest.mark.parametrize(
    'what', ["the package's SKILL.md", "the record's SKILL.md"]
)
def test_frontmatter_reasons_name_what_was_read(what):
    read = install_skill._frontmatter_name_from_bytes
    assert read(b'---\nname: x\n---\n', what) == ('x', None)
    assert read(b'skill', what) == (
        None,
        f'{what} does not begin with frontmatter',
    )
    assert read(b'---\ndescription: d\n---\n', what) == (
        None,
        f'the frontmatter of {what} has no name',
    )


# --- SKILL.md name -----------------------------------------------------------


def _check(tmp_path, skill_md, name='pdf-extract', entry='SKILL.md'):
    """The SKILL.md name _check_archive returns; ``name`` is the record's."""
    archive = tmp_path / 'package.zip'
    archive.write_bytes(make_zip({entry: skill_md}))
    return install_skill._check_archive(str(archive), name)


@pytest.mark.parametrize(
    'skill_md',
    [
        make_skill_md(),
        '---\nname: pdf-extract\n---\n',
        '---\r\nname: pdf-extract\r\ndescription: d\r\n---\r\nbody',
        '---\nname: "pdf-extract"\n---',
        "---  \nname: 'pdf-extract'  # the name\n---\t\n",
        '---\ndescription: d\nname: >-\n  pdf-extract\n---\n',
        '---\nmetadata: {author: someone}\nname: pdf-extract\n---\n',
        # Only the first 100 KiB are read, and the frontmatter is in them.
        make_skill_md(body='x' * (200 * 1024)),
        # Aliases are composed by reference, so this stays small.
        '---\na: &a [x, x, x, x, x, x, x, x, x, x]\n'
        + ''.join(f'a{i}: &a{i} [*a, *a, *a, *a, *a]\n' for i in range(30))
        + 'name: pdf-extract\n---\n',
    ],
)
def test_skill_md_name_is_read(tmp_path, skill_md):
    assert _check(tmp_path, skill_md) == 'pdf-extract'


@pytest.mark.parametrize('name', ['123', 'true', 'null', '0x1f', '1e3'])
def test_skill_md_name_is_read_as_text(tmp_path, name):
    # As the service reads it: no YAML typing turns the name into a number,
    # a boolean or nothing.
    assert _check(tmp_path, f'---\nname: {name}\n---\n') == name


@pytest.mark.parametrize('entry', ['SKILL.md', 'skill.md', 'w/skill.md'])
def test_skill_md_is_the_one_the_installer_picks(tmp_path, entry):
    assert _check(tmp_path, make_skill_md(), entry=entry) == 'pdf-extract'
    assert (
        _check(tmp_path, make_skill_md('other-name'), entry=entry)
        == 'other-name'
    )


def test_skill_md_name_is_shown_safely(tmp_path):
    with pytest.raises(AgentRegistryJWTError) as e:
        _check(
            tmp_path, '---\nname: "evil\\e[2J\\u202e' + 'x' * 1000 + '"\n---\n'
        )
    message = str(e.value)
    assert '\x1b' not in message
    assert '\u202e' not in message
    assert len(message) < 800


_NO_FRONTMATTER = "the package's SKILL.md does not begin with frontmatter"
_BOM = "the package's SKILL.md begins with a byte order mark, not frontmatter"
_BLANK_LINES = "the package's SKILL.md has blank lines before its frontmatter"
_CR_ONLY = (
    "the package's SKILL.md breaks lines with carriage returns alone, so it "
    'does not begin with a frontmatter line'
)
_NOT_CLOSED = (
    "the frontmatter of the package's SKILL.md does not end within its "
    'first 102400 bytes'
)
_NOT_YAML = "the frontmatter of the package's SKILL.md is not valid UTF-8 YAML"
_NO_NAME = "the frontmatter of the package's SKILL.md has no name"


@pytest.mark.parametrize(
    'skill_md,reason',
    [
        ('skill', _NO_FRONTMATTER),
        ('', _NO_FRONTMATTER),
        ('\ufeff' + make_skill_md(), _BOM),
        ('\n' + make_skill_md(), _BLANK_LINES),
        ('\n \r\n\t\n' + make_skill_md(), _BLANK_LINES),
        (' ---\nname: pdf-extract\n---\n', _NO_FRONTMATTER),
        ('---\rname: pdf-extract\r---\r', _CR_ONLY),
        ('name: pdf-extract\n', _NO_FRONTMATTER),
        ('----\nname: pdf-extract\n----\n', _NO_FRONTMATTER),
        ('---\nname: pdf-extract\n', _NOT_CLOSED),
        ('---\nname: pdf-extract\n--- x\n', _NOT_CLOSED),
        (
            '---\nname: pdf-extract\npad: ' + 'p' * (100 * 1024) + '\n---\n',
            _NOT_CLOSED,
        ),
        ('---\nname: [pdf-extract\n---\n', _NOT_YAML),
        ('---\nname: pdf-extract\nname: other\n---\n', _NOT_YAML),
        ('---\nname: pdf-extract\nx: ' + '[' * 5000 + '\n---\n', _NOT_YAML),
        ('---\nname: pdf\x00extract\n---\n', _NOT_YAML),
        ('---\ndescription: d\n---\n', _NO_NAME),
        ('---\n---\n', _NO_NAME),
        ('---\n- name: pdf-extract\n---\n', _NO_NAME),
        ('---\nname:\n---\n', _NO_NAME),
        ('---\nname: [pdf-extract]\n---\n', _NO_NAME),
        ('---\nname: {first: pdf-extract}\n---\n', _NO_NAME),
        ('---\n<<: {name: pdf-extract}\n---\n', _NO_NAME),
    ],
)
def test_skill_md_without_a_readable_name_is_refused(
    tmp_path, skill_md, reason
):
    with pytest.raises(AgentRegistryJWTError) as e:
        _check(tmp_path, skill_md)
    assert str(e.value) == (
        f"Refusing to install pdf-extract: {reason}, so the skill's name, "
        "which its folder is named after, can't be read."
    )


def test_skill_md_that_is_not_utf8_is_refused(tmp_path):
    with pytest.raises(AgentRegistryJWTError, match='not valid UTF-8 YAML'):
        _check(tmp_path, b'---\nname: pdf-\xffextract\n---\n')


def test_skill_md_tags_construct_no_objects(tmp_path):
    skill_md = (
        '---\nname: !!python/object/apply:os.system ["echo hacked"]\n---\n'
    )
    with patch('os.system') as system:
        with pytest.raises(AgentRegistryJWTError, match='has no name'):
            _check(tmp_path, skill_md)
    system.assert_not_called()


def test_unsafe_skill_md_name_is_refused_before_anything_is_written(
    tmp_path,
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _previous_install(folders['claude-code'], sha256='a' * 64)
    archive = make_zip({'SKILL.md': make_skill_md('../pdf-extract')})
    command, _ = _command(
        {'name': 'pdf-extract'}, archive=archive, agent_configs=configs
    )
    with pytest.raises(AgentRegistryJWTError, match='cannot name its folder'):
        _run(command, None, force=True)
    command._download.assert_called_once()
    skill = os.path.join(folders['claude-code'], 'pdf-extract')
    assert open(os.path.join(skill, 'SKILL.md')).read() == 'old'
    assert sorted(os.listdir(folders['claude-code'])) == ['pdf-extract']
    assert not os.path.exists(folders['codex'])


def test_wrapped_lower_case_skill_md_installs_end_to_end(tmp_path):
    lower = make_skill_md(body='lower')
    archive = make_zip({'my-skill/skill.md': lower, 'my-skill/a.py': 'y'})
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert sorted(os.listdir(skill)) == [PROVENANCE_MARKER, 'SKILL.md', 'a.py']
    assert (skill / 'SKILL.md').read_text() == lower


@pytest.mark.parametrize(
    'entries,expected',
    [
        ({'skill.md': 'lower'}, ['SKILL.md']),
        (
            {'my-skill/skill.md': 'lower', 'my-skill/a.py': 'y'},
            ['SKILL.md', 'a.py'],
        ),
    ],
)
def test_skill_md_in_lower_case_is_installed_as_skill_md(
    tmp_path, entries, expected
):
    out = _extract(tmp_path, make_zip(entries))
    assert _files(out) == expected
    assert (out / 'SKILL.md').read_text() == 'lower'


def test_lower_case_skill_md_installs_end_to_end(tmp_path):
    lower = make_skill_md(body='lower')
    archive = make_zip({'skill.md': lower, 'run.sh': 'echo'})
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert sorted(os.listdir(skill)) == [
        PROVENANCE_MARKER,
        'SKILL.md',
        'run.sh',
    ]
    assert (skill / 'SKILL.md').read_text() == lower


def test_root_skill_md_keeps_other_top_level_entries(tmp_path):
    out = _extract(
        tmp_path,
        make_zip({'SKILL.md': 'x', 'lib/a.py': 'y', '__MACOSX/._a': 'z'}),
    )
    assert _files(out) == sorted(
        [
            'SKILL.md',
            os.path.join('__MACOSX', '._a'),
            os.path.join('lib', 'a.py'),
        ]
    )


@pytest.mark.parametrize(
    'entries,message',
    [
        (
            {'Skill.md': 'x'},
            'The package spells SKILL.md in a casing other than SKILL.md or '
            'skill.md.',
        ),
        (
            {'SKILL.md': 'x', 'docs/SKILL.MD': 'y'},
            'The package spells SKILL.md in a casing other than SKILL.md or '
            'skill.md.',
        ),
        (
            {'SKILL.md': 'x', 'skill.md': 'y'},
            'The package spells SKILL.md in more than one casing in one '
            'directory.',
        ),
        (
            {'w/skill.md': 'x', 'w/SKILL.md': 'y'},
            'The package spells SKILL.md in more than one casing in one '
            'directory.',
        ),
        (
            {'SKILL.md': 'x', 'other/SKILL.md': 'y'},
            'The package has a SKILL.md at its root and another at the top '
            'of a directory.',
        ),
        (
            {'skill.md': 'x', 'other/skill.md': 'y'},
            'The package has a SKILL.md at its root and another at the top '
            'of a directory.',
        ),
        (
            {'a/SKILL.md': 'x', 'b/README.md': 'y'},
            'The package has more than one top-level entry and no SKILL.md '
            'at its root.',
        ),
        (
            {'my-skill/SKILL.md': 'x', '__MACOSX/my-skill/._SKILL.md': 'y'},
            'The package has more than one top-level entry and no SKILL.md '
            'at its root.',
        ),
        (
            {'README.md': 'x', 'lib/a.py': 'y'},
            'The package has more than one top-level entry and no SKILL.md '
            'at its root.',
        ),
        (
            {'README.md': 'x'},
            'The package has no SKILL.md at its root or at the top of a '
            'single top-level directory.',
        ),
        (
            {'a/b/SKILL.md': 'x'},
            'The package has no SKILL.md at its root or at the top of a '
            'single top-level directory.',
        ),
    ],
    ids=[
        'other-casing',
        'other-casing-nested',
        'both-casings',
        'both-casings-wrapped',
        'root-and-folder',
        'root-and-folder-lower',
        'two-top-level-entries',
        'macosx-next-to-wrapper',
        'no-skill-md-two-entries',
        'no-skill-md',
        'skill-md-too-deep',
    ],
)
def test_layouts_the_service_refuses_are_refused(tmp_path, entries, message):
    archive = make_zip(entries)
    with pytest.raises(AgentRegistryJWTError) as e:
        _extract(tmp_path, archive)
    assert str(e.value) == f'Not a valid skill package: {message}'
    assert not os.listdir(tmp_path / 'out')
    # Refused before any folder is touched by the command too.
    command, _ = _command({'name': 'pdf-extract'}, archive=archive)
    target = tmp_path / 'skills'
    with pytest.raises(AgentRegistryJWTError, match='Not a valid skill'):
        _run(command, target)
    assert not target.exists()


@pytest.mark.parametrize(
    'name',
    [
        f'w/{PROVENANCE_MARKER}',
        f'w/{SKILL_METADATA_FILENAME}',
        'w/lib/CON.py',
        'w/x.md ',
        f'{PROVENANCE_MARKER}/SKILL.md',
    ],
)
def test_wrapped_entries_get_every_entry_check(monkeypatch, tmp_path, name):
    # The Windows-only checks included.
    _on_windows(monkeypatch)
    archive = make_zip({'w/SKILL.md': 'x', name: 'y'})
    with pytest.raises(AgentRegistryJWTError, match='Refusing'):
        _extract(tmp_path, archive)


def test_names_after_stripping_are_checked_for_clashes():
    with pytest.raises(AgentRegistryJWTError, match='collides'):
        install_skill._check_installed_names(['SKILL.md', 'lib', 'LIB'])
    with pytest.raises(AgentRegistryJWTError, match='same path'):
        install_skill._check_installed_names(['SKILL.md', 'SKILL.md'])
    with pytest.raises(AgentRegistryJWTError, match='not a safe'):
        install_skill._check_installed_names([PROVENANCE_MARKER])
    with pytest.raises(AgentRegistryJWTError, match='not a safe'):
        install_skill._check_installed_names([SKILL_METADATA_FILENAME])


@pytest.mark.parametrize(
    'entries,message',
    [
        (
            [(zipfile.ZipInfo('SKILL.md/'), ''), ('SKILL.md/x.md', 'x')],
            'no SKILL.md at its root or at the top of a single top-level '
            'directory',
        ),
        (
            [
                (zipfile.ZipInfo('w/'), ''),
                (zipfile.ZipInfo('w/skill.md/'), ''),
            ],
            'no SKILL.md at its root or at the top of a single top-level '
            'directory',
        ),
    ],
    ids=['root', 'wrapped'],
)
def test_a_directory_named_skill_md_is_not_the_file(
    tmp_path, entries, message
):
    with pytest.raises(AgentRegistryJWTError, match=message):
        _extract(tmp_path, make_zip(entries))


def test_a_directory_named_skill_md_is_not_a_second_casing(tmp_path):
    # The directory skill.md/ is not SKILL.md spelled twice.
    out = _extract(
        tmp_path,
        make_zip(
            [
                ('w/SKILL.md', 'x'),
                (zipfile.ZipInfo('w/docs/skill.md/'), ''),
                ('w/docs/skill.md/a.md', 'y'),
            ]
        ),
    )
    assert (out / 'SKILL.md').read_text() == 'x'
    assert (out / 'docs' / 'skill.md' / 'a.md').read_text() == 'y'


def test_wrapper_directory_entry_is_not_installed(tmp_path):
    out = _extract(
        tmp_path,
        make_zip(
            [
                (zipfile.ZipInfo('w/'), ''),
                ('w/SKILL.md', 'x'),
                (zipfile.ZipInfo('w/lib/'), ''),
            ]
        ),
    )
    assert sorted(os.listdir(out)) == ['SKILL.md', 'lib']


# --- Inline SKILL.md --------------------------------------------------------


def _inline(text=SKILL_MD, source_url=None, **record):
    """A record with no package that holds ``text`` as its SKILL.md."""
    skill_md = {}
    if text is not None:
        skill_md['data'] = text
    if source_url is not None:
        skill_md['source'] = {'fromUrl': {'url': source_url}}
    record.setdefault('name', 'pdf-extract')
    record['descriptors'] = {
        'agentSkillsDefinition': {'additionalData': {'skillMd': skill_md}}
    }
    return record


def _inline_command(text=SKILL_MD, agent_configs=None, **record):
    command, client = _command(
        _inline(text, **record), agent_configs=agent_configs
    )
    response = client.batch_get_discoverable_registry_record.return_value
    del response['registryRecords'][0]['artifact']
    return command, client


def _text_digest(text=SKILL_MD):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@pytest.fixture
def no_fetching():
    """Fails the test on any HTTP request install-skill could make."""
    with (
        patch.object(
            install_skill, 'urlopen', side_effect=AssertionError('fetched')
        ) as opened,
        patch.object(
            utils, 'urlopen', side_effect=AssertionError('fetched')
        ) as utils_opened,
    ):
        yield opened, utils_opened
    opened.assert_not_called()
    utils_opened.assert_not_called()


_INLINE_STATUS = (
    'Installing the SKILL.md text published on record rec; the record has '
    'no package, so only SKILL.md is installed.'
)


def test_inline_skill_md_installs_only_skill_md(tmp_path, capsys, no_fetching):
    command, _ = _inline_command()
    assert _run(command, tmp_path) == 0
    command._download.assert_not_called()
    skill = tmp_path / 'pdf-extract'
    assert sorted(os.listdir(skill)) == [PROVENANCE_MARKER, 'SKILL.md']
    assert (skill / 'SKILL.md').read_text() == SKILL_MD
    assert _marker(skill) == dict(
        SOURCE, sha256=_text_digest(), content='skillMd'
    )
    assert _leftovers(tmp_path) == []
    err = capsys.readouterr().err
    assert _INLINE_STATUS in err.splitlines()
    assert f'Installed pdf-extract to {skill}' in err
    assert 'Downloading' not in err


@posix_only
def test_inline_skill_md_modes(tmp_path):
    command, _ = _inline_command()
    old = os.umask(0o077)
    try:
        assert _run(command, tmp_path) == 0
    finally:
        os.umask(old)
    skill = tmp_path / 'pdf-extract'
    assert stat.S_IMODE(os.stat(skill).st_mode) == 0o755
    assert stat.S_IMODE(os.stat(skill / 'SKILL.md').st_mode) == 0o644


@pytest.mark.parametrize(
    'text',
    [
        '---\r\nname: pdf-extract\r\ndescription: d\r\n---\r\nbody\r\n',
        '---\nname: pdf-extract\n---\nno trailing newline',
        '---\nname: pdf-extract\ndescription: Größe 日本 '
        '\U0001f600\n---\nété\n',
        '---\nname: pdf-extract\n---\n\n\n   trailing spaces   \n\n',
    ],
)
def test_inline_bytes_are_written_unchanged(tmp_path, no_fetching, text):
    command, _ = _inline_command(text)
    assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'SKILL.md').read_bytes() == text.encode('utf-8')
    assert _marker(skill)['sha256'] == _text_digest(text)


def test_inline_crlf_is_accepted(tmp_path, no_fetching):
    text = make_skill_md().replace('\n', '\r\n')
    command, _ = _inline_command(text)
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_bytes() == (
        text.encode()
    )


def test_inline_rerun_is_up_to_date(tmp_path, capsys, no_fetching):
    command, _ = _inline_command()
    assert _run(command, tmp_path) == 0
    capsys.readouterr()
    command, _ = _inline_command()
    with patch.object(install_skill, '_write_skill_md') as write:
        assert _run(command, tmp_path) == 0
    write.assert_not_called()
    skill = os.path.join(os.path.realpath(tmp_path), 'pdf-extract')
    assert capsys.readouterr().err.strip() == (
        f'pdf-extract is already up to date at {skill}.'
    )


def test_inline_force_reinstalls(tmp_path, capsys, no_fetching):
    command, _ = _inline_command()
    assert _run(command, tmp_path) == 0
    (tmp_path / 'pdf-extract' / 'local.txt').write_text('edit')
    command, _ = _inline_command()
    assert _run(command, tmp_path, force=True) == 0
    skill = tmp_path / 'pdf-extract'
    assert sorted(os.listdir(skill)) == [PROVENANCE_MARKER, 'SKILL.md']
    assert f'Reinstalled pdf-extract at {skill}.' in capsys.readouterr().err


def test_inline_changed_text_updates(tmp_path, capsys, no_fetching):
    command, _ = _inline_command()
    assert _run(command, tmp_path) == 0
    changed = make_skill_md(body='changed')
    command, _ = _inline_command(changed)
    assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'SKILL.md').read_text() == changed
    assert (
        f'Updated pdf-extract at {skill} ({_text_digest()[:12]}… '
        f'→ {_text_digest(changed)[:12]}…).'
    ) in capsys.readouterr().err


def test_artifact_wins_over_inline_text(tmp_path, capsys):
    command, _ = _command(_inline(make_skill_md(body='inline')))
    assert _run(command, tmp_path) == 0
    command._download.assert_called_once()
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'SKILL.md').read_text() == SKILL_MD
    assert _marker(skill)['content'] == 'package'
    assert 'Installing the SKILL.md text' not in capsys.readouterr().err


@pytest.mark.parametrize('digest', ['', 'A' * 64, 'a' * 63, None])
def test_malformed_artifact_is_refused_even_with_inline_text(
    tmp_path, no_fetching, digest
):
    record = _inline(artifact={'downloadUrl': S3_URL, 'sha256': digest})
    command, _ = _command(record)
    with pytest.raises(AgentRegistryJWTError, match='valid SHA-256 digest'):
        _run(command, tmp_path)
    command._download.assert_not_called()
    assert os.listdir(tmp_path) == []


def _package_install(folder, name='pdf-extract'):
    """A package install from SOURCE, with a script SKILL.md text lacks."""
    skill = _previous_install(
        folder, name=name, sha256=_digest(), content='package'
    )
    pathlib.Path(skill, 'lib').mkdir()
    pathlib.Path(skill, 'lib', 'a.py').write_text('code')
    return skill


def _kept(name, skill):
    return (
        f"{name} at {skill} holds the record's package; the record now "
        'publishes no downloadable package, so it was left as it is. Pass '
        '--force to replace it with the SKILL.md text only.'
    )


@pytest.mark.parametrize('folder', ['pdf-extract', 'PDF_Extract'])
def test_package_install_is_kept_when_the_record_offers_only_text(
    tmp_path, capsys, no_fetching, folder
):
    skill = _package_install(tmp_path, name=folder)
    before = _marker(skill)
    command, _ = _inline_command()
    with patch.object(install_skill, '_write_skill_md') as write:
        assert _run(command, tmp_path) == 0
    write.assert_not_called()
    assert pathlib.Path(skill, 'lib', 'a.py').read_text() == 'code'
    assert _marker(skill) == before
    assert sorted(os.listdir(tmp_path)) == [folder]
    real = os.path.join(os.path.realpath(tmp_path), folder)
    assert capsys.readouterr().err.strip() == _kept(folder, real)


def test_package_kept_in_one_folder_does_not_stop_another(
    tmp_path, capsys, no_fetching
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _package_install(folders['claude-code'])
    command, _ = _inline_command(agent_configs=configs)
    assert _run(command, None) == 0
    shared = os.path.join(folders['codex'], 'pdf-extract')
    assert sorted(os.listdir(shared)) == [PROVENANCE_MARKER, 'SKILL.md']
    err = capsys.readouterr().err
    assert "Claude Code: pdf-extract at" in err
    assert 'holds the record\'s package' in err
    assert 'Codex: Installed pdf-extract' in err


def test_other_copies_are_reported_when_the_package_is_kept(
    tmp_path, capsys, no_fetching
):
    _package_install(tmp_path)
    older = _previous_install(
        tmp_path, name='pdf_extract', sha256='a' * 64, content='skillMd'
    )
    command, _ = _inline_command()
    with patch.object(install_skill, '_write_skill_md') as write:
        assert _run(command, tmp_path) == 0
    write.assert_not_called()
    assert sorted(os.listdir(tmp_path)) == ['pdf-extract', 'pdf_extract']
    assert open(os.path.join(older, 'SKILL.md')).read() == 'old'
    assert _marker(older)['sha256'] == 'a' * 64
    real = os.path.realpath(tmp_path)
    assert capsys.readouterr().err.strip().splitlines() == [
        _kept('pdf-extract', os.path.join(real, 'pdf-extract')),
        _earlier(os.path.join(real, 'pdf_extract'), 'pdf_extract', tmp_path),
    ]


def test_force_replaces_a_package_install_with_the_text(
    tmp_path, capsys, no_fetching
):
    skill = _package_install(tmp_path)
    command, _ = _inline_command()
    assert _run(command, tmp_path, force=True) == 0
    assert sorted(os.listdir(skill)) == [PROVENANCE_MARKER, 'SKILL.md']
    assert _marker(skill)['content'] == 'skillMd'
    assert (
        f'Updated pdf-extract at {skill} (package {_digest()[:12]}… '
        f'→ SKILL.md {_text_digest()[:12]}…).'
    ) in capsys.readouterr().err


def test_package_installed_meanwhile_is_kept_too(
    tmp_path, capsys, no_fetching
):
    # Another run installed the package while this one staged the text.
    real_write = install_skill._write_skill_md

    def write(staged, data):
        real_write(staged, data)
        _package_install(os.path.dirname(staged))

    command, _ = _inline_command()
    with patch.object(install_skill, '_write_skill_md', side_effect=write):
        assert _run(command, tmp_path) == 0
    skill = tmp_path / 'pdf-extract'
    assert (skill / 'lib' / 'a.py').read_text() == 'code'
    assert _marker(skill)['content'] == 'package'
    assert _leftovers(tmp_path) == []
    assert _kept('pdf-extract', skill) in capsys.readouterr().err


def test_inline_install_updates_to_package(tmp_path, capsys):
    skill = _previous_install(
        tmp_path, sha256=_text_digest(), content='skillMd'
    )
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    command._download.assert_called_once()
    assert _marker(skill)['content'] == 'package'
    assert (
        f'Updated pdf-extract at {skill} (SKILL.md {_text_digest()[:12]}'
        f'… → package {_digest()[:12]}…).'
    ) in capsys.readouterr().err


def test_same_digest_other_content_kind_is_not_up_to_date(tmp_path, capsys):
    # The package's digest, but recorded for a SKILL.md-only install.
    skill = _previous_install(tmp_path, sha256=_digest(), content='skillMd')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path) == 0
    command._download.assert_called_once()
    assert (pathlib.Path(skill) / 'SKILL.md').read_text() == SKILL_MD
    err = capsys.readouterr().err
    assert 'already up to date' not in err
    assert 'Updated pdf-extract' in err


def test_marker_without_content_reads_as_package(tmp_path):
    skill = _previous_install(tmp_path)
    assert 'content' not in _marker(skill)
    assert install_skill.read_provenance(skill) == dict(
        SOURCE, content='package'
    )


@pytest.mark.parametrize('content', [7, None, ['x'], {'kind': 'zip'}])
def test_marker_with_non_text_content_is_unreadable(tmp_path, capsys, content):
    skill = _previous_install(tmp_path, content=content)
    assert install_skill.read_provenance(skill) is None
    # So never replaced, nor counted as installed.
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    assert (pathlib.Path(skill) / 'SKILL.md').read_text() == 'old'
    assert 'no readable' in capsys.readouterr().err


_NEWER = (
    'it was installed by a newer version of the AWS CLI, which this one '
    'does not understand. Update the AWS CLI to install or update the skill '
    'here.'
)


@pytest.mark.parametrize('content', ['zip', 'SKILLMD', '', 'Package'])
def test_marker_with_unknown_content_is_kept_as_given(tmp_path, content):
    skill = _previous_install(tmp_path, content=content)
    assert install_skill.read_provenance(skill) == dict(
        SOURCE, content=content
    )


@pytest.mark.parametrize('force', [False, True])
@pytest.mark.parametrize('folder', ['pdf-extract', 'other-name'])
@pytest.mark.parametrize('inline', [False, True])
def test_install_refuses_to_replace_a_newer_clis_install(
    tmp_path, capsys, force, folder, inline
):
    skill = _previous_install(
        tmp_path, name=folder, sha256=_digest(), content='zipV2'
    )
    if inline:
        command, _ = _inline_command()
    else:
        command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=force) == 1
    # Found by its marker before anything is downloaded or written.
    command._download.assert_not_called()
    assert sorted(os.listdir(tmp_path)) == [folder]
    assert (pathlib.Path(skill) / 'SKILL.md').read_text() == 'old'
    real = os.path.join(os.path.realpath(tmp_path), folder)
    assert capsys.readouterr().err.strip() == (
        f'Refusing to replace {real}: {_NEWER}'
    )


def test_newer_clis_install_from_another_source_is_refused_too(
    tmp_path, capsys
):
    skill = _previous_install(
        tmp_path, registryId='otherREG123456', content='zipV2'
    )
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, force=True) == 1
    assert (pathlib.Path(skill) / 'SKILL.md').read_text() == 'old'
    assert _NEWER in capsys.readouterr().err


def test_newer_clis_install_meanwhile_is_kept(tmp_path, capsys):
    def newer(destination):
        _previous_install(os.path.dirname(destination), content='zipV2')

    command, _ = _command({'name': 'pdf-extract'})
    with _change_during_extraction(newer):
        assert _run(command, tmp_path, force=True) == 1
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    assert _leftovers(tmp_path) == []
    assert _NEWER in capsys.readouterr().err


def test_outcome_names_an_unknown_content_safely():
    line = install_skill._outcome(
        install_skill._UPDATE,
        'x',
        '/skills/x',
        dict(SOURCE, content='new\x1b[2J'),
        dict(SOURCE, sha256='b' * 64, content='package'),
    )
    assert '\x1b' not in line
    assert "'new\\x1b[2J' 000000000000… → package bbbbbbbbbbbb…" in line


_LINK = 'https://raw.githubusercontent.com/org/repo/main/SKILL.md?token=s3cr3t'


@pytest.mark.parametrize('text', [None, '', '  \n\t', 7])
def test_url_only_skill_md_is_refused_without_fetching(
    tmp_path, no_fetching, text
):
    command, _ = _inline_command(text, source_url=_LINK)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    command._download.assert_not_called()
    assert os.listdir(tmp_path) == []
    assert str(e.value) == (
        'Record rec publishes its SKILL.md only as a link to '
        'https://raw.githubusercontent.com. install-skill does not fetch '
        'from hosts a publisher chooses; the publisher must upload a package '
        'or put the SKILL.md text in the record.'
    )


def test_inline_text_with_source_url_installs_and_never_fetches(
    tmp_path, capsys, no_fetching
):
    command, _ = _inline_command(source_url=_LINK)
    assert _run(command, tmp_path) == 0
    command._download.assert_not_called()
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    err = capsys.readouterr().err
    assert 'githubusercontent' not in err
    assert 's3cr3t' not in err


@pytest.mark.parametrize(
    'descriptors',
    [
        None,
        'text',
        {},
        {'agentSkillsDefinition': None},
        {'agentSkillsDefinition': ['x']},
        {'agentSkillsDefinition': {}},
        {'agentSkillsDefinition': {'additionalData': 'x'}},
        {'agentSkillsDefinition': {'additionalData': {}}},
        {'agentSkillsDefinition': {'additionalData': {'skillMd': 'x'}}},
        {'agentSkillsDefinition': {'additionalData': {'skillMd': {}}}},
        _inline(None)['descriptors'],
        _inline('')['descriptors'],
        _inline(' \r\n')['descriptors'],
        _inline(7)['descriptors'],
        _inline(['text'])['descriptors'],
        _inline(None, source_url='')['descriptors'],
        {
            'agentSkillsDefinition': {
                'additionalData': {'skillMd': {'source': {'fromUrl': 'x'}}}
            }
        },
        # The descriptor's own data is not SKILL.md.
        {'agentSkillsDefinition': {'data': SKILL_MD}},
    ],
)
@pytest.mark.parametrize('artifact', [None, {}, {'sha256': 'a' * 64}])
def test_record_without_package_or_text_is_refused(
    tmp_path, no_fetching, descriptors, artifact
):
    record = {'name': 'pdf-extract'}
    if descriptors is not None:
        record['descriptors'] = descriptors
    command, client = _command(record)
    response = client.batch_get_discoverable_registry_record.return_value
    record = response['registryRecords'][0]
    if artifact is None:
        del record['artifact']
    else:
        record['artifact'] = artifact
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert str(e.value) == (
        'Record rec has no downloadable package and no SKILL.md text, so '
        'there is nothing to install.'
    )
    command._download.assert_not_called()
    assert os.listdir(tmp_path) == []


def _text_of_length(length, filler='x'):
    head = make_skill_md(body='')
    return head + filler * (length - len(head))


@pytest.mark.parametrize('filler', ['x', 'é', '\U0001f600'])
def test_inline_text_at_the_cap_installs(tmp_path, no_fetching, filler):
    text = _text_of_length(102_400, filler)
    assert len(text) == install_skill.MAX_SKILL_MD_CHARACTERS
    command, _ = _inline_command(text)
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_bytes() == (
        text.encode('utf-8')
    )


def test_inline_text_over_the_cap_is_refused(tmp_path, no_fetching):
    command, _ = _inline_command(_text_of_length(102_401))
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert str(e.value) == (
        'Refusing to install record rec: its SKILL.md text has more than the '
        "102,400 characters a record's SKILL.md can hold."
    )
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize('surrogate', ['\ud800', '\udfff', 'a\udc80b'])
def test_inline_lone_surrogate_is_refused(tmp_path, no_fetching, surrogate):
    command, _ = _inline_command(make_skill_md(body=surrogate))
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert str(e.value) == (
        'Refusing to install record rec: its SKILL.md text is not valid '
        'Unicode text.'
    )
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    'text', [make_skill_md(body='a\x00b'), '---\nname: pdf\x00extract\n---\n']
)
def test_inline_nul_is_refused(tmp_path, no_fetching, text):
    command, _ = _inline_command(text)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert str(e.value) == (
        'Refusing to install record rec: its SKILL.md text contains a NUL '
        'character.'
    )
    assert os.listdir(tmp_path) == []


def _inline_refusal(reason):
    return (
        f"Refusing to install pdf-extract: the {reason}, so the skill's name, "
        "which its folder is named after, can't be read."
    )


@pytest.mark.parametrize(
    'text,reason',
    [
        (
            '﻿' + SKILL_MD,
            "record's SKILL.md begins with a byte order mark, not frontmatter",
        ),
        (
            '\n\n' + SKILL_MD,
            "record's SKILL.md has blank lines before its frontmatter",
        ),
        (
            ' \r\n' + SKILL_MD,
            "record's SKILL.md has blank lines before its frontmatter",
        ),
        (
            SKILL_MD.replace('\n', '\r'),
            "record's SKILL.md breaks lines with carriage returns alone, so "
            'it does not begin with a frontmatter line',
        ),
    ],
)
def test_inline_bom_leading_blank_lines_and_cr_only_are_refused(
    tmp_path, no_fetching, text, reason
):
    command, _ = _inline_command(text)
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path)
    assert str(e.value) == _inline_refusal(reason)
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    'text,reason',
    [
        ('just text', "record's SKILL.md does not begin with frontmatter"),
        (
            '---\nname: pdf-extract\n',
            "frontmatter of the record's SKILL.md does not end within its "
            'first 102400 bytes',
        ),
        (
            '---\nname: [pdf-extract\n---\n',
            "frontmatter of the record's SKILL.md is not valid UTF-8 YAML",
        ),
        (
            '---\ndescription: d\n---\n',
            "frontmatter of the record's SKILL.md has no name",
        ),
        (
            '---\nname: !!python/object/apply:os.system ["echo x"]\n---\n',
            "frontmatter of the record's SKILL.md has no name",
        ),
    ],
)
def test_inline_frontmatter_problems_are_refused(
    tmp_path, no_fetching, text, reason
):
    command, _ = _inline_command(text)
    with patch('os.system') as system:
        with pytest.raises(AgentRegistryJWTError) as e:
            _run(command, tmp_path)
    system.assert_not_called()
    assert str(e.value) == _inline_refusal(reason)
    assert os.listdir(tmp_path) == []


def test_inline_name_rules_are_the_packages(tmp_path, capsys, no_fetching):
    command, _ = _inline_command(make_skill_md('../evil'))
    with pytest.raises(AgentRegistryJWTError, match='cannot name its folder'):
        _run(command, tmp_path)
    command, _ = _inline_command(make_skill_md('PDF_Extract'))
    assert _run(command, tmp_path) == 0
    assert (tmp_path / 'PDF_Extract' / 'SKILL.md').is_file()
    err = capsys.readouterr().err
    assert err.count('Warning: PDF_Extract is not an Agent Skills name') == 1
    assert "Record 'pdf-extract' installs as skill 'PDF_Extract'." in err


def test_inline_status_line_prints_only_after_the_name_check(
    tmp_path, capsys, no_fetching
):
    for text, match in [
        ('---\ndescription: d\n---\n', 'has no name'),
        (make_skill_md('../evil'), 'cannot name its folder'),
    ]:
        command, _ = _inline_command(text)
        with pytest.raises(AgentRegistryJWTError, match=match):
            _run(command, tmp_path)
        assert 'Installing the SKILL.md text' not in capsys.readouterr().err
    assert os.listdir(tmp_path) == []

    command, _ = _inline_command()
    assert _run(command, tmp_path) == 0
    lines = capsys.readouterr().err.splitlines()
    installed = f'Installed pdf-extract to {tmp_path / "pdf-extract"}'
    assert lines.index(_INLINE_STATUS) < lines.index(installed)


@pytest.mark.parametrize('force', [False, True])
@pytest.mark.parametrize('occupant', ['other source', 'no marker', 'link'])
def test_inline_refuses_other_source_unmarked_and_symlinked_destinations(
    tmp_path, capsys, no_fetching, occupant, force
):
    target = tmp_path / 'skills'
    target.mkdir()
    if occupant == 'other source':
        _previous_install(target, registryId='otherREG123456')
        expected = 'it was installed from registry otherREG123456'
    elif occupant == 'no marker':
        _previous_install(target, marker=False)
        expected = f'it has no readable {PROVENANCE_MARKER}'
    else:
        elsewhere = _previous_install(tmp_path / 'elsewhere')
        os.symlink(elsewhere, target / 'pdf-extract')
        expected = 'outside'
    command, _ = _inline_command()
    assert _run(command, target, force=force) == 1
    assert expected in capsys.readouterr().err
    if occupant == 'link':
        assert os.path.islink(target / 'pdf-extract')
    else:
        assert (target / 'pdf-extract' / 'SKILL.md').read_text() == 'old'
    assert _leftovers(target) == []


def test_inline_swap_is_a_same_directory_rename(tmp_path, no_fetching):
    _previous_install(tmp_path, sha256='a' * 64, content='skillMd')
    renames = []
    real_rename = os.rename

    def rename(source, destination):
        renames.append((source, destination))
        return real_rename(source, destination)

    command, _ = _inline_command()
    with patch.object(install_skill.os, 'rename', side_effect=rename):
        assert _run(command, tmp_path) == 0
    # The old copy aside, the staged one into place.
    assert len(renames) == 2
    for source, destination in renames:
        assert os.path.dirname(source) == os.path.dirname(destination)
    assert renames[1][1] == os.path.join(
        os.path.realpath(tmp_path), 'pdf-extract'
    )
    assert _leftovers(tmp_path) == []


def test_inline_text_is_never_printed(tmp_path, capsys, caplog, no_fetching):
    secret = 'SECRET-SKILL-TEXT-1234'
    text = f'---\nname: pdf-extract\ndescription: {secret}\n---\n{secret}\n'
    caplog.set_level(logging.DEBUG)
    command, _ = _inline_command(text)
    assert _run(command, tmp_path) == 0
    command, _ = _inline_command(text.replace('name: pdf-extract', 'name: ['))
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(command, tmp_path / 'other')
    captured = capsys.readouterr()
    for output in (captured.out, captured.err, caplog.text, str(e.value)):
        assert secret not in output


# --- Agents -----------------------------------------------------------------


def test_agent_argument_is_agent_toolkits():
    [argument] = [
        arg for arg in InstallSkillCommand.ARG_TABLE if arg['name'] == 'agent'
    ]
    assert argument == dict(AGENT_ARG, help_text=argument['help_text'])
    assert argument['help_text'].startswith(AGENT_ARG['help_text'])
    for config in AGENT_CONFIGS:
        assert config.id in argument['help_text']
    assert InstallSkillCommand(Mock())._agent_configs is AGENT_CONFIGS


def test_default_installs_into_every_detected_agent_once_per_folder(
    tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None) == 0
    for agent in ('claude-code', 'codex'):
        skill = os.path.join(folders[agent], 'pdf-extract', 'SKILL.md')
        assert open(skill).read() == SKILL_MD
    # Cursor is not installed on this machine.
    assert not os.path.exists(folders['cursor'])
    # Downloaded and verified once.
    command._download.assert_called_once()
    err = capsys.readouterr().err
    claude = os.path.join(folders['claude-code'], 'pdf-extract')
    shared = os.path.join(folders['codex'], 'pdf-extract')
    assert f'Claude Code: Installed pdf-extract to {claude}' in err
    # Codex and Gemini CLI share a folder: one line for it.
    assert f'Codex: Installed pdf-extract to {shared}' in err
    assert 'Gemini CLI' not in err


def test_agent_installs_into_that_agent_only(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None, agent='Claude-Code') == 0
    assert os.path.isdir(os.path.join(folders['claude-code'], 'pdf-extract'))
    assert not os.path.exists(folders['codex'])


def test_agent_and_target_directory_cannot_be_combined(tmp_path):
    configs, _ = make_agents(str(tmp_path / 'home'))
    command, client = _command({'name': 'pdf-extract'}, agent_configs=configs)
    with pytest.raises(ParamValidationError, match='--target-directory'):
        _run(command, tmp_path / 'skills', agent='claude-code')
    command._session.create_client.assert_not_called()
    client.batch_get_discoverable_registry_record.assert_not_called()


@pytest.mark.parametrize('agent', [None, 'cursor'])
def test_no_detected_agent_fails_like_agent_toolkit(tmp_path, agent):
    configs, _ = make_agents(str(tmp_path / 'home'), detected=())
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    with pytest.raises(ParamValidationError) as e:
        _run(command, None, agent=agent)
    message = str(e.value)
    assert message.startswith('No supported AI coding agents found.')
    # What to do instead.
    assert '--target-directory <dir>' in message
    assert '--agent <id>' in message
    command._session.create_client.assert_not_called()


def test_unknown_agent_is_refused(tmp_path):
    configs, _ = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    with pytest.raises(ParamValidationError, match='Invalid agent "vim"'):
        _run(command, None, agent='vim')
    command._session.create_client.assert_not_called()


def test_a_failed_folder_does_not_stop_the_others(tmp_path, capsys):
    configs, folders = make_agents(str(tmp_path / 'home'))
    os.makedirs(folders['claude-code'])
    os.symlink(tmp_path, os.path.join(folders['claude-code'], 'pdf-extract'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None, force=True) == 1
    assert os.path.isdir(os.path.join(folders['codex'], 'pdf-extract'))
    assert os.path.islink(os.path.join(folders['claude-code'], 'pdf-extract'))
    err = capsys.readouterr().err
    assert 'Claude Code: Refusing' in err
    assert 'Codex: Installed' in err


def test_an_install_failure_in_one_folder_does_not_stop_the_others(
    tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    real_extract = install_skill._safe_extract

    def fail_for_claude(archive, staged):
        if staged.startswith(os.path.realpath(folders['claude-code'])):
            raise OSError('read-only file system')
        return real_extract(archive, staged)

    with patch.object(
        install_skill, '_safe_extract', side_effect=fail_for_claude
    ):
        assert _run(command, None) == 1
    assert not os.path.exists(
        os.path.join(folders['claude-code'], 'pdf-extract')
    )
    assert os.path.isdir(os.path.join(folders['codex'], 'pdf-extract'))
    assert _leftovers(folders['claude-code']) == []
    err = capsys.readouterr().err
    assert 'Claude Code: Could not install pdf-extract' in err
    assert 'read-only file system' in err


def test_nothing_is_downloaded_when_every_folder_is_up_to_date(
    tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    for agent in ('claude-code', 'codex'):
        _previous_install(folders[agent], sha256=_digest())
    command, _ = _command({'name': 'pdf-extract'}, agent_configs=configs)
    assert _run(command, None) == 0
    command._download.assert_not_called()
    err = capsys.readouterr().err
    assert err.count('pdf-extract is already up to date at') == 2


# --- Authorization ----------------------------------------------------------


@pytest.mark.parametrize('authorizer', [None, 'JWT'])
def test_endpoint_with_a_query_is_refused_before_any_call(
    tmp_path, auth_env, monkeypatch, endpoint, authorizer
):
    # The real resolution, on a real session.
    endpoint.side_effect = utils.resolve_data_plane_endpoint
    for name in list(os.environ):
        if name.startswith('AWS_ENDPOINT_URL'):
            monkeypatch.delenv(name)
    monkeypatch.setenv('AWS_CONFIG_FILE', str(tmp_path / 'config'))
    session = botocore.session.Session()
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[botocore.loaders.Loader.BUILTIN_DATA_PATH],
            include_default_search_paths=False,
        ),
    )
    command = InstallSkillCommand(session, agent_configs=[])
    args = argparse.Namespace(
        registry_id=REGISTRY_ID,
        record_id='rec',
        record_name=None,
        target_directory=str(tmp_path / 'skills'),
        agent=None,
        force=False,
        authorizer=authorizer,
        client_id='client',
        no_browser=True,
    )
    globals_ = argparse.Namespace(
        region='us-west-2',
        endpoint_url='https://registry.example?x=1',
        verify_ssl=None,
        ca_bundle=None,
    )
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
        pytest.raises(AgentRegistryJWTError, match='--endpoint-url'),
    ):
        command._run_main(args, globals_)
    load.assert_not_called()
    sign_in.assert_not_called()
    assert not (tmp_path / 'skills').exists()


def test_jwt_install_uses_cached_token(tmp_path, auth_env, endpoint):
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token', return_value='tok') as load:
        assert (
            _run(command, tmp_path, authorizer='JWT', ca_bundle='/corp.pem')
            == 0
        )
    assert os.environ['AWS_BEARER_TOKEN_AGENT_REGISTRY'] == 'tok'
    assert 'AWS_AUTH_SCHEME_PREFERENCE' not in os.environ
    config = command._session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'
    assert load.call_args.kwargs['ca_bundle'] == '/corp.pem'
    # Looked up at the endpoint the call goes to, resolved like a data plane
    # command's.
    assert load.call_args.args == (ENDPOINT, REGISTRY_ID)
    session, globals_, region = endpoint.call_args.args
    assert session is command._session
    assert region == 'us-west-2'


def test_jwt_install_leaves_a_user_preference_alone(
    tmp_path, auth_env, monkeypatch, endpoint
):
    monkeypatch.setenv('AWS_AUTH_SCHEME_PREFERENCE', 'sigv4')
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token', return_value='tok'):
        assert _run(command, tmp_path, authorizer='JWT') == 0
    # The client's own config selects the bearer scheme, ahead of it.
    assert os.environ['AWS_AUTH_SCHEME_PREFERENCE'] == 'sigv4'
    config = command._session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'


def test_jwt_install_uses_a_preset_token_as_is(
    tmp_path, auth_env, monkeypatch, endpoint
):
    monkeypatch.setenv('AWS_BEARER_TOKEN_AGENT_REGISTRY', 'minted-elsewhere')
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token') as load:
        assert _run(command, tmp_path, authorizer='JWT') == 0
    load.assert_not_called()
    # Still resolved, for the provenance marker, and https only.
    assert endpoint.call_args.kwargs == {'https_only': True}
    assert os.environ['AWS_BEARER_TOKEN_AGENT_REGISTRY'] == 'minted-elsewhere'
    config = command._session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'


def test_jwt_install_with_a_preset_token_still_refuses_no_verify_ssl(
    tmp_path, auth_env, monkeypatch
):
    monkeypatch.setenv('AWS_BEARER_TOKEN_AGENT_REGISTRY', 'minted-elsewhere')
    command, _ = _command({'name': 'pdf-extract'})
    with pytest.raises(AgentRegistryJWTError, match='--ca-bundle'):
        _run(command, tmp_path, authorizer='JWT', verify_ssl=False)
    command._session.create_client.assert_not_called()


def test_jwt_install_with_an_arn_uses_the_registry_id_sign_in(
    tmp_path, auth_env, endpoint
):
    command, client = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token', return_value='tok') as load:
        assert (
            _run(command, tmp_path, authorizer='JWT', registry_id=REGISTRY_ARN)
            == 0
        )
    # Same cache entry as the bare id, while the API gets the ARN as given.
    assert load.call_args.args == (ENDPOINT, REGISTRY_ID)
    entries = client.batch_get_discoverable_registry_record.call_args.kwargs[
        'entries'
    ]
    assert entries == [{'registryId': REGISTRY_ARN, 'recordIds': ['rec']}]


@pytest.mark.parametrize(
    'registry_id', ['reg', '../../evil', f'{REGISTRY_ID}\n', 'a' * 17]
)
def test_jwt_install_refuses_a_malformed_registry_id(
    tmp_path, auth_env, registry_id
):
    command, client = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token') as load:
        with pytest.raises(AgentRegistryJWTError, match='registry identifier'):
            _run(command, tmp_path, authorizer='JWT', registry_id=registry_id)
    load.assert_not_called()
    command._session.create_client.assert_not_called()


def test_jwt_install_refuses_no_verify_ssl(tmp_path, auth_env):
    command, client = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token') as load:
        with pytest.raises(AgentRegistryJWTError) as e:
            _run(command, tmp_path, authorizer='JWT', verify_ssl=False)
    assert "TLS verification can't be disabled" in str(e.value)
    assert '--ca-bundle' in str(e.value)
    load.assert_not_called()
    command._session.create_client.assert_not_called()
    command._download.assert_not_called()
    assert 'AWS_BEARER_TOKEN_AGENT_REGISTRY' not in os.environ


def test_sigv4_install_still_honors_no_verify_ssl(tmp_path):
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, verify_ssl=False) == 0
    create_client = command._session.create_client
    assert create_client.call_args.kwargs['verify'] is False


# --- Revision 4: reads, pre-set token, sign-in miss -------------------------


class _BrokenResponse:
    def __init__(self, error):
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        raise self._error


@pytest.mark.parametrize(
    'error',
    [
        TimeoutError('The read operation timed out'),
        ConnectionResetError(54, 'Connection reset by peer'),
        http.client.IncompleteRead(b'PK', 100),
        http.client.RemoteDisconnected(''),
    ],
    ids=['timeout', 'reset', 'incomplete', 'disconnected'],
)
def test_download_read_errors_are_reported_cleanly(tmp_path, error):
    with patch.object(
        install_skill, 'urlopen', return_value=_BrokenResponse(error)
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            InstallSkillCommand(Mock())._download(S3_URL, str(tmp_path / 'a'))
    message = str(e.value)
    assert message.startswith(
        'Download from https://bucket.s3.us-west-2.amazonaws.com failed: '
    )
    assert not message.endswith(': ')
    _assert_no_query(message)


def test_jwt_install_with_a_preset_token_says_so(
    tmp_path, auth_env, monkeypatch, capsys
):
    monkeypatch.setenv('AWS_BEARER_TOKEN_AGENT_REGISTRY', 'minted-elsewhere')
    command, _ = _command({'name': 'pdf-extract'})
    assert _run(command, tmp_path, authorizer='JWT') == 0
    assert (
        'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
        'sign-in, --client-id and --no-browser are not used.'
    ) in capsys.readouterr().err


def test_jwt_install_remembers_the_sign_in_for_the_401_hint(
    tmp_path, auth_env, signed_in_registry
):
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token', return_value='tok'):
        assert _run(command, tmp_path, authorizer='JWT') == 0
    assert signed_in_registry['registry_id'] == REGISTRY_ID


# --- Sign-in from install-skill ---------------------------------------------


def _token_at_batch_get(client):
    """Record the bearer token in the environment when BatchGet is called."""
    seen = []
    response = client.batch_get_discoverable_registry_record.return_value

    def batch_get(**kwargs):
        seen.append(os.environ.get('AWS_BEARER_TOKEN_AGENT_REGISTRY'))
        return response

    client.batch_get_discoverable_registry_record.side_effect = batch_get
    return seen


def test_jwt_install_without_a_cached_token_signs_in_first(
    tmp_path, auth_env, endpoint
):
    command, client = _command({'name': 'pdf-extract'})
    seen = _token_at_batch_get(client)
    with (
        patch.object(cache, 'load_token', return_value=None),
        patch.object(
            providers, 'sign_in', return_value='signed-in-token'
        ) as sign_in,
    ):
        assert (
            _run(
                command,
                tmp_path,
                authorizer='JWT',
                ca_bundle='/corp.pem',
                registry_id=REGISTRY_ARN,
            )
            == 0
        )
    # The shared sign-in, at the endpoint the call goes to, before BatchGet.
    sign_in.assert_called_once_with(
        command._session,
        ENDPOINT,
        REGISTRY_ID,
        client_id=None,
        ca_bundle='/corp.pem',
        open_browser=True,
    )
    assert seen == ['signed-in-token']


def test_jwt_install_with_no_browser_signs_in_without_opening_one(
    tmp_path, auth_env
):
    command, _ = _command({'name': 'pdf-extract'})
    with (
        patch.object(cache, 'load_token', return_value=None),
        patch.object(providers, 'sign_in', return_value='t') as sign_in,
    ):
        assert _run(command, tmp_path, authorizer='JWT', no_browser=True) == 0
    assert sign_in.call_args.kwargs['open_browser'] is False


def test_jwt_install_with_a_cached_token_does_not_sign_in(tmp_path, auth_env):
    command, client = _command({'name': 'pdf-extract'})
    seen = _token_at_batch_get(client)
    with (
        patch.object(cache, 'load_token', return_value='tok'),
        patch.object(providers, 'sign_in') as sign_in,
    ):
        assert _run(command, tmp_path, authorizer='JWT') == 0
    sign_in.assert_not_called()
    assert seen == ['tok']


def test_jwt_install_passes_the_client_id_on(tmp_path, auth_env):
    command, _ = _command({'name': 'pdf-extract'})
    with (
        patch.object(cache, 'load_token', return_value=None) as load,
        patch.object(providers, 'sign_in', return_value='t') as sign_in,
    ):
        assert (
            _run(command, tmp_path, authorizer='JWT', client_id='my-client')
            == 0
        )
    # A cached sign-in for another client is a miss, as for data-plane calls.
    assert load.call_args.kwargs['client_id'] == 'my-client'
    assert sign_in.call_args.kwargs['client_id'] == 'my-client'


def test_no_verify_ssl_is_refused_before_any_sign_in(tmp_path, auth_env):
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(providers, 'sign_in') as sign_in:
        with pytest.raises(AgentRegistryJWTError, match='--ca-bundle'):
            _run(command, tmp_path, authorizer='JWT', verify_ssl=False)
    sign_in.assert_not_called()


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
def test_sigv4_install_never_signs_in(tmp_path, auth_env, authorizer):
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(providers, 'sign_in') as sign_in:
        assert _run(command, tmp_path, authorizer=authorizer) == 0
    sign_in.assert_not_called()


def test_client_id_is_ignored_with_sigv4(tmp_path, auth_env):
    # As for the data plane commands, --client-id only matters with JWT.
    command, client = _command({'name': 'pdf-extract'})
    with patch.object(cache, 'load_token') as load:
        assert _run(command, tmp_path, authorizer='SIGV4', client_id='x') == 0
    load.assert_not_called()
    client.batch_get_discoverable_registry_record.assert_called_once()


def test_jwt_install_with_a_preset_token_does_not_sign_in(
    tmp_path, auth_env, monkeypatch
):
    monkeypatch.setenv('AWS_BEARER_TOKEN_AGENT_REGISTRY', 'minted-elsewhere')
    command, _ = _command({'name': 'pdf-extract'})
    with patch.object(providers, 'sign_in') as sign_in:
        assert _run(command, tmp_path, authorizer='JWT', client_id='x') == 0
    sign_in.assert_not_called()


# The shared sign-in, run for real: only HTTP and the browser are not.

_ISSUER = 'https://idp.example.com'
_OIDC = {
    'issuer': _ISSUER,
    'authorization_endpoint': f'{_ISSUER}/authorize',
    'token_endpoint': f'{_ISSUER}/token',
}


def _discovery(scopes=None):
    prm = {'authorization_servers': [_ISSUER]}
    if scopes is not None:
        prm['scopes_supported'] = scopes

    def get_json(url, **kwargs):
        return prm if 'oauth-protected-resource' in url else _OIDC

    return patch.object(utils, 'http_get_json', side_effect=get_json)


def _browser_returns(token):
    from awscli.customizations.agentregistry import providers

    return patch.object(
        providers, 'run_browser_login', return_value={'access_token': token}
    )


def test_install_sign_in_caches_the_token_and_uses_it(tmp_path, auth_env):
    from tests.unit.customizations.agentregistry.utils import make_jwt

    token = make_jwt(sub='user')
    command, client = _command({'name': 'pdf-extract'})
    seen = _token_at_batch_get(client)
    with (
        _discovery(scopes=['registry:read']),
        _browser_returns(token) as login,
    ):
        assert (
            _run(command, tmp_path, authorizer='JWT', client_id='my-client')
            == 0
        )
    assert seen == [token]
    assert login.call_args.kwargs['client_id'] == 'my-client'
    assert login.call_args.kwargs['scopes'] == ['openid', 'registry:read']
    entry = cache.read_entry(ENDPOINT, REGISTRY_ID)
    assert entry['accessToken'] == token
    assert entry['clientId'] == 'my-client'
    assert entry['issuer'] == _ISSUER


def test_install_sign_in_reuses_the_cached_client_id(
    tmp_path, auth_env, capsys
):
    from tests.unit.customizations.agentregistry.utils import make_jwt

    # Expired, with nothing to refresh it with.
    cache.save_token(
        ENDPOINT,
        REGISTRY_ID,
        token=make_jwt(exp=1),
        expires_in=1,
        refresh_token=None,
        client_id='cached-client',
        issuer=_ISSUER,
    )
    command, _ = _command({'name': 'pdf-extract'})
    with _discovery(), _browser_returns(make_jwt()) as login:
        assert _run(command, tmp_path, authorizer='JWT') == 0
    assert login.call_args.kwargs['client_id'] == 'cached-client'
    assert (
        'Using client id cached-client from the previous sign-in.'
        in capsys.readouterr().err
    )


def test_install_sign_in_without_a_terminal_or_client_id_explains(
    tmp_path, auth_env
):
    from awscli.customizations.agentregistry import providers

    command, client = _command({'name': 'pdf-extract'})
    with (
        _discovery(),
        _browser_returns('t') as login,
        patch.object(providers, 'stdin_is_terminal', return_value=False),
    ):
        with pytest.raises(AgentRegistryJWTError, match='Pass --client-id'):
            _run(command, tmp_path, authorizer='JWT')
    login.assert_not_called()
    client.batch_get_discoverable_registry_record.assert_not_called()


def test_install_skill_has_the_shared_sign_in_arguments():
    names = [argument['name'] for argument in InstallSkillCommand.ARG_TABLE]
    assert names == [
        'registry-id',
        'record-id',
        'record-name',
        'agent',
        'target-directory',
        'authorizer',
        'client-id',
        'no-browser',
        'force',
    ]
    shared = [
        argument
        for argument in InstallSkillCommand.ARG_TABLE
        if argument['name'] in ('authorizer', 'client-id', 'no-browser')
    ]
    assert shared == dataplane.SIGN_IN_ARGUMENTS
    [authorizer] = [arg for arg in shared if arg['name'] == 'authorizer']
    assert (
        'If there is no usable cached sign-in, you sign in through the '
        'browser and the new sign-in is cached.'
    ) in authorizer['help_text']
    assert InstallSkillCommand.DESCRIPTION.endswith(
        dataplane.SIGN_IN_DESCRIPTION
    )
    assert (
        'signs you in through the browser if there is no usable cached '
        'sign-in'
    ) in InstallSkillCommand.DESCRIPTION
    assert '``list-skills``' in InstallSkillCommand.DESCRIPTION


# --- By record name ---------------------------------------------------------

RECORD_ID = 'r1s2t3u4v5w6'


def _summary(name, record_id, **fields):
    """A record summary as ListDiscoverableRegistryRecords returns it."""
    record = {
        'recordId': record_id,
        'recordArn': f'{REGISTRY_ARN}/record/{record_id}',
        'name': name,
        'recordType': 'SKILL',
    }
    record.update(fields)
    return record


PDF_SUMMARY = _summary('pdf-extract', RECORD_ID)
CSV_SUMMARY = _summary('csv-tools', 'recCSV000001')
DOCX_SUMMARY = _summary('docx-tools', 'recDOCX00001')


def _named_command(*pages, record=None):
    """install-skill whose listing returns ``pages``, one page each.

    The listing's ``requested`` holds the index of every page read so far.
    """
    command, client = _command(
        dict(record or {'name': 'pdf-extract'}, recordId=RECORD_ID)
    )
    requested = []

    def paginate(**kwargs):
        for index, page in enumerate(pages):
            requested.append(index)
            yield {'registryRecords': list(page)}

    paginator = client.get_paginator.return_value
    paginator.paginate.side_effect = paginate
    paginator.requested = requested
    return command, client


def _batch_get_ids(client):
    return [
        entry['recordIds']
        for call in client.batch_get_discoverable_registry_record.mock_calls
        for entry in call.kwargs['entries']
    ]


def test_name_found_on_the_first_page_still_reads_every_page(tmp_path, capsys):
    command, client = _named_command(
        [CSV_SUMMARY, PDF_SUMMARY], [DOCX_SUMMARY]
    )
    assert (
        _run(command, tmp_path, record_id=None, record_name='pdf-extract') == 0
    )
    paginator = client.get_paginator.return_value
    client.get_paginator.assert_called_once_with(
        'list_discoverable_registry_records'
    )
    # The listing list-skills reads: the registry as given, skills only.
    paginator.paginate.assert_called_once_with(
        registryId=REGISTRY_ID,
        filters=[{'name': 'recordType', 'values': ['SKILL']}],
        PaginationConfig={'PageSize': 100},
    )
    # Found on the first page, but a same-named record could be on a later
    # one, so every page is read.
    assert paginator.requested == [0, 1]
    assert _batch_get_ids(client) == [[RECORD_ID]]
    err = capsys.readouterr().err
    assert f"Record 'pdf-extract' is {RECORD_ID}." in err
    # The status line comes first, then the install goes on as by id.
    assert err.index(f"is {RECORD_ID}.") < err.index('Downloading')
    assert f'Installed pdf-extract to {tmp_path / "pdf-extract"}' in err
    assert (tmp_path / 'pdf-extract' / 'SKILL.md').read_text() == SKILL_MD
    assert _marker(tmp_path / 'pdf-extract')['recordId'] == RECORD_ID


def test_name_is_looked_up_on_every_page(tmp_path, capsys):
    command, client = _named_command(
        [CSV_SUMMARY], [], [DOCX_SUMMARY, PDF_SUMMARY], [CSV_SUMMARY]
    )
    assert (
        _run(command, tmp_path, record_id=None, record_name='pdf-extract') == 0
    )
    # The page after the match is read too, and holds no other match.
    assert client.get_paginator.return_value.requested == [0, 1, 2, 3]
    assert _batch_get_ids(client) == [[RECORD_ID]]
    assert f"Record 'pdf-extract' is {RECORD_ID}." in capsys.readouterr().err


def test_name_installs_as_the_same_record_id_would(tmp_path):
    by_name, _ = _named_command([PDF_SUMMARY])
    assert (
        _run(
            by_name, tmp_path / 'a', record_id=None, record_name='pdf-extract'
        )
        == 0
    )
    by_id, _ = _command({'name': 'pdf-extract', 'recordId': RECORD_ID})
    assert _run(by_id, tmp_path / 'b', record_id=RECORD_ID) == 0
    assert _marker(tmp_path / 'a' / 'pdf-extract') == _marker(
        tmp_path / 'b' / 'pdf-extract'
    )
    assert _files(tmp_path / 'a') == _files(tmp_path / 'b')


def _refused_by_name(tmp_path, command, client, name, match):
    with pytest.raises(AgentRegistryJWTError, match=match) as e:
        _run(command, tmp_path / 'skills', record_id=None, record_name=name)
    client.batch_get_discoverable_registry_record.assert_not_called()
    command._download.assert_not_called()
    assert not (tmp_path / 'skills').exists()
    return str(e.value)


def test_unknown_name_is_refused_after_every_page(tmp_path):
    command, client = _named_command([CSV_SUMMARY], [DOCX_SUMMARY])
    message = _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'has no skill record'
    )
    assert message == (
        f"Registry {REGISTRY_ID} has no skill record named 'pdf-extract'; "
        f"--record-name matches the record's name (name in list-skills), "
        f'not its SKILL.md name (skillName). Run aws agent-registry '
        f'list-skills --registry-id {REGISTRY_ID} to see the names.'
    )
    assert client.get_paginator.return_value.requested == [0, 1]
    # The other records' names are not listed.
    assert 'csv-tools' not in message


def test_a_skill_md_name_is_not_a_record_name(tmp_path):
    # The record is named otherwise; its SKILL.md names the skill
    # pdf-extract, as skillName in list-skills would show.
    summary = _inline(
        name='pdf_processing_skill',
        recordId=RECORD_ID,
        recordType='SKILL',
        skillName='pdf-extract',
    )
    command, client = _named_command([summary])
    message = _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'has no skill record'
    )
    # The refusal says which name is matched.
    assert "--record-name matches the record's name" in message
    assert 'not its SKILL.md name (skillName)' in message


@pytest.mark.parametrize('name', ['PDF-Extract', 'pdf-extract ', 'pdf'])
def test_name_must_match_exactly(tmp_path, name):
    command, client = _named_command([PDF_SUMMARY])
    _refused_by_name(tmp_path, command, client, name, 'has no skill record')


@pytest.mark.parametrize(
    'record',
    [
        _summary('pdf-extract', RECORD_ID, recordType='MCP'),
        _summary('pdf-extract', RECORD_ID, recordType=None),
        _summary('pdf-extract', None),
        _summary('pdf-extract', ''),
        'pdf-extract',
    ],
)
def test_only_installable_skill_records_match(tmp_path, record):
    command, client = _named_command([record])
    _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'has no skill record'
    )


def test_two_records_with_the_name_are_refused_with_both_ids(tmp_path):
    other = _summary('pdf-extract', 'recPDF000002')
    command, client = _named_command(
        [PDF_SUMMARY, CSV_SUMMARY, other], [DOCX_SUMMARY]
    )
    message = _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'more than one'
    )
    # Neither summary has a recordVersion, so only the ids are listed.
    assert message == (
        f"Registry {REGISTRY_ID} has more than one skill record named "
        f"'pdf-extract': {RECORD_ID}, recPDF000002. Pass --record-id to "
        f'choose one.'
    )
    assert client.get_paginator.return_value.requested == [0, 1]


def test_same_named_records_on_different_pages_are_refused(tmp_path):
    # As in a real registry: two APPROVED versions of one skill, as
    # separate records with the same name, a page apart.
    first = _summary(
        'pdf_processing_skill', 'd2sH0PxSVTmM', recordVersion='1.0.0'
    )
    second = _summary(
        'pdf_processing_skill', 'VtdOzKjGABnO', recordVersion='1.0.1'
    )
    command, client = _named_command(
        [CSV_SUMMARY, first], [DOCX_SUMMARY, second]
    )
    message = _refused_by_name(
        tmp_path, command, client, 'pdf_processing_skill', 'more than one'
    )
    assert message == (
        f'Registry {REGISTRY_ID} has more than one skill record named '
        f"'pdf_processing_skill': d2sH0PxSVTmM (1.0.0), VtdOzKjGABnO "
        f'(1.0.1). Pass --record-id to choose one.'
    )
    assert client.get_paginator.return_value.requested == [0, 1]


@pytest.mark.parametrize('version', [None, '', 7])
def test_a_match_without_a_usable_version_is_listed_by_id(tmp_path, version):
    first = _summary('pdf-extract', RECORD_ID, recordVersion='1.0.0')
    second = _summary('pdf-extract', 'recPDF000002', recordVersion=version)
    command, client = _named_command([first], [second])
    message = _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'more than one'
    )
    assert f': {RECORD_ID} (1.0.0), recPDF000002. Pass' in message


def test_same_named_records_are_listed_safely(tmp_path):
    first = _summary('pdf-extract', 'r1\x1b[31m', recordVersion='1\x1b[2J')
    command, client = _named_command([first], [PDF_SUMMARY])
    message = _refused_by_name(
        tmp_path, command, client, 'pdf-extract', 'more than one'
    )
    assert '\x1b' not in message
    assert f'r1 [31m (1 [2J), {RECORD_ID}.' in message


@pytest.mark.parametrize(
    'pages', [[[PDF_SUMMARY, PDF_SUMMARY]], [[PDF_SUMMARY], [PDF_SUMMARY]]]
)
def test_a_record_listed_twice_is_one_match(tmp_path, pages):
    command, client = _named_command(*pages)
    assert (
        _run(command, tmp_path, record_id=None, record_name='pdf-extract') == 0
    )
    assert _batch_get_ids(client) == [[RECORD_ID]]


def test_name_and_registry_text_are_printed_safely(tmp_path, capsys):
    name = 'pdf\x1b[2J-extract'
    record_id = 'r1s2\x1b[31mt3'
    command, client = _named_command([_summary(name, record_id)])
    with pytest.raises(AgentRegistryJWTError):
        # BatchGet returns another record, so the install stops there.
        _run(command, tmp_path, record_id=None, record_name=name)
    err = capsys.readouterr().err
    assert "Record 'pdf\\x1b[2J-extract' is r1s2 [31mt3." in err
    assert '\x1b' not in err
    missing, client = _named_command([])
    with pytest.raises(AgentRegistryJWTError) as e:
        _run(missing, tmp_path, record_id=None, record_name=name)
    assert '\x1b' not in str(e.value)


@pytest.mark.parametrize(
    'record_id,name', [(None, None), ('rec', 'pdf-extract'), ('', '')]
)
def test_exactly_one_of_record_id_and_record_name_before_any_call(
    tmp_path, auth_env, endpoint, record_id, name
):
    command, client = _named_command([PDF_SUMMARY])
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
        pytest.raises(
            ParamValidationError,
            match='Specify exactly one of --record-id and --record-name.',
        ),
    ):
        _run(
            command,
            tmp_path / 'skills',
            authorizer='JWT',
            record_id=record_id,
            record_name=name,
        )
    load.assert_not_called()
    sign_in.assert_not_called()
    endpoint.assert_not_called()
    command._session.create_client.assert_not_called()
    client.get_paginator.assert_not_called()
    client.batch_get_discoverable_registry_record.assert_not_called()
    assert not (tmp_path / 'skills').exists()


def test_jwt_name_lookup_and_install_share_one_sign_in(tmp_path, auth_env):
    command, client = _named_command([PDF_SUMMARY])
    seen = _token_at_batch_get(client)
    listed = []
    paginate = client.get_paginator.return_value.paginate.side_effect

    def paginate_with_token(**kwargs):
        listed.append(os.environ.get('AWS_BEARER_TOKEN_AGENT_REGISTRY'))
        return paginate(**kwargs)

    client.get_paginator.return_value.paginate.side_effect = (
        paginate_with_token
    )
    with (
        patch.object(cache, 'load_token', return_value=None),
        patch.object(providers, 'sign_in', return_value='tok') as sign_in,
    ):
        assert (
            _run(
                command,
                tmp_path,
                authorizer='JWT',
                record_id=None,
                record_name='pdf-extract',
            )
            == 0
        )
    sign_in.assert_called_once()
    # One client, signed in once, for the listing and the BatchGet.
    command._session.create_client.assert_called_once()
    config = command._session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'
    assert listed == ['tok']
    assert seen == ['tok']


def test_skill_record_pages_keep_only_skill_records():
    client = Mock()
    client.get_paginator.return_value.paginate.return_value = iter(
        [
            {'registryRecords': [PDF_SUMMARY, 'x', {'recordType': 'MCP'}]},
            {},
            {'registryRecords': None},
            {'registryRecords': [CSV_SUMMARY]},
        ]
    )
    pages = dataplane.skill_record_pages(client, REGISTRY_ARN)
    assert list(pages) == [[PDF_SUMMARY], [], [], [CSV_SUMMARY]]
    # The most the service returns in a page, so the fewest calls.
    client.get_paginator.return_value.paginate.assert_called_once_with(
        registryId=REGISTRY_ARN,
        filters=[{'name': 'recordType', 'values': ['SKILL']}],
        PaginationConfig={'PageSize': 100},
    )


def test_record_id_is_no_longer_required_and_record_name_is_documented():
    arguments = {
        argument['name']: argument
        for argument in InstallSkillCommand.ARG_TABLE
    }
    assert not arguments['record-id'].get('required')
    assert not arguments['record-name'].get('required')
    # Not --name, which uninstall-skill takes as the installed skill's name.
    assert 'name' not in arguments
    help_text = arguments['record-name']['help_text']
    for text in (
        '<code>list-skills</code>',
        'exactly',
        '<code>skillName</code>',
        'agent-registry:ListDiscoverableRegistryRecords',
        '<code>--record-id</code>',
        'more than one',
    ):
        assert text in help_text
    assert '<code>--record-name</code>' in arguments['record-id']['help_text']
    assert '``--record-name``' in InstallSkillCommand.DESCRIPTION
    assert '``--name``' not in InstallSkillCommand.DESCRIPTION
    assert (
        '``agent-registry:ListDiscoverableRegistryRecords``'
        in InstallSkillCommand.DESCRIPTION
    )
