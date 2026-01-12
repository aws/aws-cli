# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys

from awscli.customizations.s3.syncstrategy.base import BaseSync
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)


class CaseConflictException(Exception):
    pass


class CaseConflictSync(BaseSync):
    DOC_URI = (
        "https://docs.aws.amazon.com/cli/v1/topic/"
        "s3-case-insensitivity.html"
    )

    def __init__(
            self,
            sync_type='file_not_at_dest',
            on_case_conflict='ignore',
            submitted=None,
    ):
        super().__init__(sync_type)
        self._on_case_conflict = on_case_conflict
        if submitted is None:
            submitted = set()
        self._submitted = submitted

    @property
    def submitted(self):
        return self._submitted

    def determine_should_sync(self, src_file, dest_file):
        # `src_file.compare_key` and `dest_file.compare_key` are not equal.
        # This could mean that they're completely different or differ
        # only by case. eg, `/tmp/a` and `/tmp/b` versus `/tmp/a` and `/tmp/A`.
        # If the source file's destination already exists, that means it
        # differs only by case and the conflict needs to be handled.
        should_sync = True
        # Normalize compare key for case sensitivity.
        lower_compare_key = src_file.compare_key.lower()
        if lower_compare_key in self._submitted or os.path.exists(
                src_file.dest
        ):
            handler = getattr(self, f"_handle_{self._on_case_conflict}")
            should_sync = handler(src_file)
        if should_sync:
            LOG.debug(f"syncing: {src_file.src} -> {src_file.dest}")
            self._submitted.add(lower_compare_key)
            # Set properties so that a subscriber can be created
            # that removes the key from the set after download finishes.
            src_file.case_conflict_submitted = self._submitted
            src_file.case_conflict_key = lower_compare_key
        return should_sync

    @staticmethod
    def _handle_ignore(src_file):
        return True

    @staticmethod
    def _handle_skip(src_file):
        msg = (
            f"warning: Skipping {src_file.src} -> {src_file.dest} "
            "because a file whose name differs only by case either exists "
            "or is being downloaded.\n"
        )
        uni_print(msg, sys.stderr)
        return False

    @staticmethod
    def _handle_warn(src_file):
        msg = (
            f"warning: Downloading {src_file.src} -> {src_file.dest} "
            "despite a file whose name differs only by case either existing "
            "or being downloaded. This behavior is not defined on "
            "case-insensitive filesystems and may result in overwriting "
            "existing files or race conditions between concurrent downloads. "
            f"For more information, see {CaseConflictSync.DOC_URI}.\n"
        )
        uni_print(msg, sys.stderr)
        return True

    @staticmethod
    def _handle_error(src_file):
        msg = (
            f"Failed to download {src_file.src} -> {src_file.dest} "
            "because a file whose name differs only by case either exists "
            "or is being downloaded."
        )
        raise CaseConflictException(msg)
