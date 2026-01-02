# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging


LOG = logging.getLogger(__name__)

VALID_SYNC_TYPES = ['file_at_src_and_dest', 'file_not_at_dest',
                    'file_not_at_src']


class BaseSync(object):
    """Base sync strategy

    To create a new sync strategy, subclass from this class.
    """

    # This is the argument that will be added to the ``SyncCommand`` arg table.
    # This argument will represent the sync strategy when the arguments for
    # the sync command are parsed.  ``ARGUMENT`` follows the same format as
    # a member of ``ARG_TABLE`` in ``BasicCommand`` class as specified in
    # ``awscli/customizations/commands.py``.
    #
    # For example, if I wanted to perform the sync strategy whenever I type
    # ``--my-sync-strategy``, I would say:
    #
    # ARGUMENT =
    #     {'name': 'my-sync-strategy', 'action': 'store-true',
    #      'help_text': 'Performs my sync strategy'}
    #
    # Typically, the argument's ``action`` should ``store_true`` to
    # minimize amount of extra code in making a custom sync strategy.
    ARGUMENT = None

    # At this point all that need to be done is implement
    # ``determine_should_sync`` method (see method for more information).

    def __init__(self, sync_type='file_at_src_and_dest'):
        """
        :type sync_type: string
        :param sync_type: This determines where the sync strategy will be
            used. There are three strings to choose from:

            'file_at_src_and_dest': apply sync strategy on a file that
            exists both at the source and the destination.

            'file_not_at_dest': apply sync strategy on a file that
            exists at the source but not the destination.

            'file_not_at_src': apply sync strategy on a file that
            exists at the destination but not the source.
        """
        self._check_sync_type(sync_type)
        self._sync_type = sync_type

    def _check_sync_type(self, sync_type):
        if sync_type not in VALID_SYNC_TYPES:
            raise ValueError("Unknown sync_type: %s.\n"
                             "Valid options are %s." %
                             (sync_type, VALID_SYNC_TYPES))

    @property
    def sync_type(self):
        return self._sync_type

    def register_strategy(self, session):
        """Registers the sync strategy class to the given session."""

        session.register('building-arg-table.sync',
                         self.add_sync_argument)
        session.register('choosing-s3-sync-strategy', self.use_sync_strategy)

    def determine_should_sync(self, src_file, dest_file):
        """Subclasses should implement this method.

        This function takes two ``FileStat`` objects (one from the source and
        one from the destination).  Then makes a decision on whether a given
        operation (e.g. a upload, copy, download) should be allowed
        to take place.

        The function currently raises a ``NotImplementedError``.  So this
        method must be overwritten when this class is subclassed.  Note
        that this method must return a Boolean as documented below.

        :type src_file: ``FileStat`` object
        :param src_file: A representation of the operation that is to be
            performed on a specific file existing in the source.  Note if
            the file does not exist at the source, ``src_file`` is None.

        :type dest_file: ``FileStat`` object
        :param dest_file: A representation of the operation that is to be
            performed on a specific file existing in the destination. Note if
            the file does not exist at the destination, ``dest_file`` is None.

        :rtype: Boolean
        :return: True if an operation based on the ``FileStat`` should be
            allowed to occur.
            False if if an operation based on the ``FileStat`` should not be
            allowed to occur. Note the operation being referred to depends on
            the ``sync_type`` of the sync strategy:

            'file_at_src_and_dest': refers to ``src_file``

            'file_not_at_dest': refers to ``src_file``

            'file_not_at_src': refers to ``dest_file``
         """

        raise NotImplementedError("determine_should_sync")

    @property
    def arg_name(self):
        # Retrieves the ``name`` of the sync strategy's ``ARGUMENT``.
        name = None
        if self.ARGUMENT is not None:
            name = self.ARGUMENT.get('name', None)
        return name

    @property
    def arg_dest(self):
        # Retrieves the ``dest`` of the sync strategy's ``ARGUMENT``.
        dest = None
        if self.ARGUMENT is not None:
            dest = self.ARGUMENT.get('dest', None)
        return dest

    def add_sync_argument(self, arg_table, **kwargs):
        # This function adds sync strategy's argument to the ``SyncCommand``
        # argument table.
        if self.ARGUMENT is not None:
            arg_table.append(self.ARGUMENT)

    def use_sync_strategy(self, params, **kwargs):
        # This function determines which sync strategy the ``SyncCommand`` will
        # use. The sync strategy object must be returned by this method
        # if it is to be chosen as the sync strategy to use.
        #
        # ``params`` is a dictionary that specifies all of the arguments
        # the sync command is able to process as well as their values.
        #
        # Since ``ARGUMENT`` was added to the ``SyncCommand`` arg table,
        # the argument will be present in ``params``.
        #
        # If the argument was included in the actual ``aws s3 sync`` command
        # its value will show up as ``True`` in ``params`` otherwise its value
        # will be ``False`` in ``params`` assuming the argument's ``action``
        # is ``store_true``.
        #
        # Note: If the ``action`` of ``ARGUMENT`` was not set to
        # ``store_true``, this method will need to be overwritten.
        #
        name_in_params = None
        # Check if a ``dest`` was specified in ``ARGUMENT`` as if it is
        # specified, the boolean value will be located at the argument's
        # ``dest`` value in the ``params`` dictionary.
        if self.arg_dest is not None:
            name_in_params = self.arg_dest
        # Then check ``name`` of ``ARGUMENT``, the boolean value will be
        # located at the argument's ``name`` value in the ``params``
        # dictionary.
        elif self.arg_name is not None:
            # ``name`` has all ``-`` replaced with ``_`` in ``params``.
            name_in_params = self.arg_name.replace('-', '_')
        if name_in_params is not None:
            if params.get(name_in_params):
                # Return the sync strategy object to be used for syncing.
                return self
        return None

    def total_seconds(self, td):
        """
        timedelta's time_seconds() function for python 2.6 users

        :param td: The difference between two datetime objects.
        """
        return (td.microseconds + (td.seconds + td.days * 24 *
                                   3600) * 10**6) / 10**6

    def compare_size(self, src_file, dest_file):
        """
        :returns: True if the sizes are the same.
            False otherwise.
        """
        return src_file.size == dest_file.size

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
            if self.total_seconds(delta) >= 0:
                # Destination is newer than source.
                return True
            else:
                # Destination is older than source, so
                # we have a more recently updated file
                # at the source location.
                return False
        elif cmd == "download":

            if self.total_seconds(delta) <= 0:
                return True
            else:
                # delta is positive, so the destination
                # is newer than the source.
                return False


class SizeAndLastModifiedSync(BaseSync):

    def determine_should_sync(self, src_file, dest_file):
        same_size = self.compare_size(src_file, dest_file)
        same_last_modified_time = self.compare_time(src_file, dest_file)
        should_sync = (not same_size) or (not same_last_modified_time)
        if should_sync:
            LOG.debug(
                "syncing: %s -> %s, size: %s -> %s, modified time: %s -> %s",
                src_file.src, src_file.dest,
                src_file.size, dest_file.size,
                src_file.last_update, dest_file.last_update)
        return should_sync


class NeverSync(BaseSync):
    def __init__(self, sync_type='file_not_at_src'):
        super(NeverSync, self).__init__(sync_type)

    def determine_should_sync(self, src_file, dest_file):
        return False


class MissingFileSync(BaseSync):
    def __init__(self, sync_type='file_not_at_dest'):
        super(MissingFileSync, self).__init__(sync_type)

    def determine_should_sync(self, src_file, dest_file):
        LOG.debug("syncing: %s -> %s, file does not exist at destination",
                  src_file.src, src_file.dest)
        return True
