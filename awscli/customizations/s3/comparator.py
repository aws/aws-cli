# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
from six import advance_iterator


LOG = logging.getLogger(__name__)


def total_seconds(td):
    """
    timedelta's time_seconds() function for python 2.6 users
    """
    return (td.microseconds + (td.seconds + td.days * 24 *
                               3600) * 10**6) / 10**6


class Comparator(object):
    """
    This class performs all of the comparisons behind the sync operation
    """
    def __init__(self, params=None):
        self.delete = False
        if 'delete' in params:
            self.delete = params['delete']

        self.compare_on_size_only = False
        if 'size_only' in params:
            self.compare_on_size_only = params['size_only']

        self.match_exact_timestamps = False
        if 'exact_timestamps' in params:
            self.match_exact_timestamps = params['exact_timestamps']

    def call(self, src_files, dest_files):
        """
        This function preforms the actual comparisons.  The parameters it takes
        are the generated files for both the source and the destination.  The
        key concept in this function is that no matter the type of where the
        files are coming from, they are listed in the same order, least to
        greatest in collation order.  This allows for easy comparisons to
        determine if file needs to be added or deleted.  Comparison keys are
        used to determine if two files are the same and each file has a
        unique comparison key.  If they are the same compare the size and
        last modified times to see if a file needs to be updated.   Ultimately,
        it will yield a sequence of file info objectsthat will be sent to
        the ``S3Handler``.

        :param src_files: The generated FileInfo objects from the source.
        :param dest_files: The genereated FileInfo objects from the dest.

        :returns: Yields the FilInfo objects of the files that need to be
            operated on

        Algorithm:
            Try to take next from both files. If it is empty signal
            corresponding done flag.  If both generated lists are not done
            compare compare_keys.  If equal, compare size and time to see if
            it needs to be updated.  If source compare_key is less than dest
            compare_key, the file needs to be added to the destination.  Take
            the next source file but not not destination file.  If the source
            compare_key is greater than dest compare_key, that destination file
            needs to be deleted from the destination.  Take the next dest file
            but not the source file.  If the source list is empty delete the
            rest of the files in the dest list from the destination.  If the
            dest list is empty add the rest of the file in source list to
            the destionation.
        """
        # :var src_done: True if there are no more files from the source left.
        src_done = False
        # :var dest_done: True if there are no more files form the dest left.
        dest_done = False
        # :var src_take: Take the next source file from the generated files if
        #     true
        src_take = True
        # :var dest_take: Take the next dest file from the generated files if
        #     true
        dest_take = True
        while True:
            try:
                if (not src_done) and src_take:
                    src_file = advance_iterator(src_files)
            except StopIteration:
                src_file = None
                src_done = True
            try:
                if (not dest_done) and dest_take:
                    dest_file = advance_iterator(dest_files)
            except StopIteration:
                dest_file = None
                dest_done = True

            if (not src_done) and (not dest_done):
                src_take = True
                dest_take = True

                compare_keys = self.compare_comp_key(src_file, dest_file)

                if compare_keys == 'equal':
                    same_size = self.compare_size(src_file, dest_file)
                    same_last_modified_time = self.compare_time(src_file, dest_file)

                    if self.compare_on_size_only:
                        should_sync = not same_size
                    else:
                        should_sync = (not same_size) or (not same_last_modified_time)

                    if should_sync:
                        LOG.debug("syncing: %s -> %s, size_changed: %s, "
                                  "last_modified_time_changed: %s",
                                  src_file.src, src_file.dest,
                                  not same_size, not same_last_modified_time)
                        yield src_file
                elif compare_keys == 'less_than':
                    src_take = True
                    dest_take = False
                    LOG.debug("syncing: %s -> %s, file does not exist at destination",
                            src_file.src, src_file.dest)
                    yield src_file

                elif compare_keys == 'greater_than':
                    src_take = False
                    dest_take = True
                    dest_file.operation_name = 'delete'
                    if self.delete:
                        LOG.debug("syncing: (None) -> %s (remove), file does "
                                  "not exist at source (%s) and delete "
                                  "mode enabled",
                                  dest_file.src, dest_file.dest)
                        yield dest_file

            elif (not src_done) and dest_done:
                src_take = True
                LOG.debug("syncing: %s -> %s, file does not exist "
                          "at destination",
                          src_file.src, src_file.dest)
                yield src_file

            elif src_done and (not dest_done):
                dest_take = True
                dest_file.operation_name = 'delete'
                if self.delete:
                    LOG.debug("syncing: (None) -> %s (remove), file does not "
                              "exist at source (%s) and delete mode enabled",
                              dest_file.src, dest_file.dest)
                    yield dest_file
            else:
                break

    def compare_size(self, src_file, dest_file):
        """
        :returns: True if the sizes are the same.
            False otherwise.
        """
        return src_file.size == dest_file.size

    def compare_comp_key(self, src_file, dest_file):
        """
        Determines if the source compare_key is less than, equal to,
        or greater than the destination compare_key
        """

        src_comp_key = src_file.compare_key
        dest_comp_key = dest_file.compare_key
        if (src_comp_key == dest_comp_key):
            return 'equal'

        elif (src_comp_key < dest_comp_key):
            return 'less_than'

        else:
            return 'greater_than'

    def compare_time(self, src_file, dest_file):
        """
        :returns: True if the file does not need updating based on time of
            last modification and type of operation.
            False if the file does need updating based on the time of
            last modification and type of operation.
        """
        src_time = src_file.last_update
        dest_time = dest_file.last_update
        delta = dest_time - src_time
        cmd = src_file.operation_name
        if cmd == "upload" or cmd == "copy":
            if total_seconds(delta) >= 0:
                # Destination is newer than source.
                return True
            else:
                # Destination is older than source, so
                # we have a more recently updated file
                # at the source location.
                return False
        elif cmd == "download":
            if self.match_exact_timestamps:
                # An update is needed unless the
                # timestamps match exactly.
                return total_seconds(delta) == 0

            if total_seconds(delta) <= 0:
                return True
            else:
                # delta is positive, so the destination
                # is newer than the source.
                return False
