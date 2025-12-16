# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import pytest

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.syncstrategy.caseconflict import (
    CaseConflictException,
    CaseConflictSync,
)


@pytest.fixture
def lower_compare_key():
    return 'a.txt'


@pytest.fixture
def lower_temp_filepath(lower_compare_key, tmp_path):
    p = tmp_path / lower_compare_key
    return p.resolve()


@pytest.fixture
def lower_file_stat(lower_compare_key, lower_temp_filepath):
    return FileStat(
        src=f'bucket/{lower_compare_key}',
        dest=lower_temp_filepath,
        compare_key=lower_compare_key,
    )


@pytest.fixture
def upper_compare_key():
    return 'A.txt'


@pytest.fixture
def upper_temp_filepath(upper_compare_key, tmp_path):
    p = tmp_path / upper_compare_key
    p.write_text('foobar')
    return p.resolve()


@pytest.fixture
def upper_file_stat(upper_compare_key, upper_temp_filepath):
    return FileStat(
        src=f'bucket/{upper_compare_key}',
        dest=upper_temp_filepath,
        compare_key=upper_compare_key,
    )


@pytest.fixture
def upper_key(upper_file_stat):
    return upper_file_stat.compare_key.lower()


@pytest.fixture
def no_conflict_file_stat(tmp_path):
    return FileStat(
        src='bucket/foo.txt',
        # Note that this file was never written to.
        dest=f'{tmp_path}/foo.txt',
        compare_key='foo.txt',
    )


class TestCaseConflictSync:
    def test_error_with_no_conflict_syncs(
        self, no_conflict_file_stat, lower_file_stat, capsys
    ):
        case_conflict = CaseConflictSync(on_case_conflict='error')
        should_sync = case_conflict.determine_should_sync(
            no_conflict_file_stat, lower_file_stat
        )
        captured = capsys.readouterr()
        assert should_sync is True
        assert not captured.err

    def test_error_with_existing_file(self, lower_file_stat, upper_file_stat):
        case_conflict_sync = CaseConflictSync(on_case_conflict='error')
        with pytest.raises(CaseConflictException) as exc:
            case_conflict_sync.determine_should_sync(
                lower_file_stat,
                upper_file_stat,
            )
        assert 'Failed to download bucket/a.txt' in str(exc.value)

    def test_error_with_case_conflicts_in_s3(
        self, lower_file_stat, upper_file_stat, upper_key
    ):
        case_conflict_sync = CaseConflictSync(
            on_case_conflict='error', submitted={upper_key}
        )
        with pytest.raises(CaseConflictException) as exc:
            case_conflict_sync.determine_should_sync(
                lower_file_stat,
                upper_file_stat,
            )
        assert 'Failed to download bucket/a.txt' in str(exc.value)

    def test_warn_with_no_conflict_syncs(
        self, no_conflict_file_stat, lower_file_stat, capsys
    ):
        case_conflict = CaseConflictSync(on_case_conflict='warn')
        should_sync = case_conflict.determine_should_sync(
            no_conflict_file_stat, lower_file_stat
        )
        captured = capsys.readouterr()
        assert should_sync is True
        assert not captured.err

    def test_warn_with_existing_file(
        self, lower_file_stat, upper_file_stat, capsys
    ):
        case_conflict_sync = CaseConflictSync(on_case_conflict='warn')
        should_sync = case_conflict_sync.determine_should_sync(
            lower_file_stat, upper_file_stat
        )
        captured = capsys.readouterr()
        assert should_sync is True
        assert 'warning: ' in captured.err

    def test_warn_with_case_conflicts_in_s3(
        self, lower_file_stat, upper_file_stat, upper_key, capsys
    ):
        case_conflict_sync = CaseConflictSync(
            on_case_conflict='warn', submitted={upper_key}
        )
        should_sync = case_conflict_sync.determine_should_sync(
            lower_file_stat,
            upper_file_stat,
        )
        captured = capsys.readouterr()
        assert should_sync is True
        assert 'warning: ' in captured.err

    def test_skip_with_no_conflict_syncs(
        self, no_conflict_file_stat, lower_file_stat, capsys
    ):
        case_conflict = CaseConflictSync(on_case_conflict='skip')
        should_sync = case_conflict.determine_should_sync(
            no_conflict_file_stat, lower_file_stat
        )
        captured = capsys.readouterr()
        assert should_sync is True
        assert not captured.err

    def test_skip_with_existing_file(
        self, lower_file_stat, upper_file_stat, capsys
    ):
        case_conflict_sync = CaseConflictSync(on_case_conflict='skip')
        should_sync = case_conflict_sync.determine_should_sync(
            lower_file_stat, upper_file_stat
        )
        captured = capsys.readouterr()
        assert should_sync is False
        assert 'warning: Skipping' in captured.err

    def test_skip_with_case_conflicts_in_s3(
        self, lower_file_stat, upper_file_stat, upper_key, capsys
    ):
        case_conflict_sync = CaseConflictSync(
            on_case_conflict='skip', submitted={upper_key}
        )
        should_sync = case_conflict_sync.determine_should_sync(
            lower_file_stat,
            upper_file_stat,
        )
        captured = capsys.readouterr()
        assert should_sync is False
        assert 'warning: Skipping' in captured.err
