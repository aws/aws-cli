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


SIZE_ONLY = {'name': 'size-only', 'action': 'store_true',
             'help_text': (
                 'Makes the size of each key the only criteria used to '
                 'decide whether to sync from source to destination.')}

EXACT_TIMESTAMPS = {'name': 'exact-timestamps', 'action': 'store_true',
                    'help_text': (
                        'When syncing from S3 to local, same-sized '
                        'items will be ignored only when the timestamps '
                        'match exactly. The default behavior is to ignore '
                        'same-sized items unless the local version is newer '
                        'than the S3 version.')}


def register_sync_strategies(command_table, session, **kwargs):
    """Registers the different sync strategies.

    To register a sync strategy add
    ``register_sync_strategy(session, YourSyncStrategyClass)``
    to the list of registered strategies in this function.
    """

    # Register the size only sync strategy.
    register_sync_strategy(session, SizeOnlySyncStrategy)

    # Register the exact timestamps sync strategy.
    register_sync_strategy(session, ExactTimestampsSyncStrategy)

    # Register additional sync strategies here...


def register_sync_strategy(session, strategy_cls):
    """Registers a single sync strategy

    :param session: The session that the sync strategy is being registered to.
    :param strategy_cls: the class of the sync strategy to be registered.
    """
    strategy = strategy_cls()
    strategy.register_strategy(session)


def total_seconds(td):
    """
    timedelta's time_seconds() function for python 2.6 users
    """
    return (td.microseconds + (td.seconds + td.days * 24 *
                               3600) * 10**6) / 10**6


class BaseSyncStrategy(object):
    """Basic sync strategy

    To create a new sync strategy, subclass from this class.
    """

    # This is the argument that will be added to the ``SyncCommand`` arg table.
    # This argument will represent the sync strategy when the arguments for
    # the sync command are parsed.  ARGUMENT follows the same format as
    # a member of ARG_TABLE in ``BasicCommand`` class as specified in
    # ``awscli/customizations/commands.py``.
    #
    # For example, if I wanted to perform the sync strategy whenever I type
    # ``--my-sync-strategy, I would say:
    #
    # ARGUMENT =
    #     {'name': 'my-sync-strategy', 'action': 'store-true',
    #      'help_text': 'Performs my sync strategy'}
    #
    # Typically, the argument's ``action`` should ``store_true`` to
    # minimize amount of extra code in making a custom sync strategy.
    ARGUMENT = None

    # At this point all that need to be done is implement
    # ``compare_same_name_files`` method (see method for more information).

    def __init__(self):
        pass

    def register_strategy(self, session):
        """Registers the sync strategy class to the given session."""

        session.register('initiate-building-arg-table', self._add_sync_argument)
        session.register('choosing-s3-sync-strategy', self._use_sync_strategy)

    def compare_same_name_files(self, src_file, dest_file):
        """Subclasses should implement this method.

        This function takes two files (one in the source and one in the
        destination) that share the same name and relative location.  Then
        compares the two files to decide if the file at the source needs to
        replace the file at the destination.

        The function currently raises a ``NotImplementedError``.  So this
        method must be overwritten when this class is subclassed.  Note
        that this method must return a Boolean as documented below.

        :type src_file: ``FileStat`` object
        :param src_file: A representation of the file existing in the source.

        :type dest_file: ``FileStat`` object
        :param dest_file: A representation of the file existing in the
            destination.

        :rtype: Boolean
        :return: True if the file at the source needs to be transfered to the
            destination. False if the file at the source does not need to
            be transfered to the destination.
        """

        raise NotImplementedError("compare_same_name_files")

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

    def _add_sync_argument(self, arg_table, session, **kwargs):
        # This function adds sync strategy's argument to the ``SyncCommand``
        # argument table.
        if self.ARGUMENT is not None:
            arg_table.append(self.ARGUMENT)

    def _use_sync_strategy(self, params, **kwargs):
        # This function determines which sync strategy the ``SyncCommand`` will
        # use. The sync strategy object must be returned by this method
        # if it is to be chosen as the sync strategy to use.
        #
        # ``params`` is a dictionary that specifies the all of the arguments
        # the sync command is able to process as well as their values.
        #
        # Since ``ARGUMENT`` was added to the ``SyncCommand`` arg table,
        # the argument will be present in ``params``.
        #
        # If the argument was included in the actual ``aws s3 sync`` command
        # its value will show up as ``True`` in ``params`` otherwise its value
        # will be ``False`` in ``params``.
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
        # located at the argument's ``name`` value in the ``params`` dictionary.
        elif self.arg_name is not None:
            # ``name`` has all ``-`` replaced with ``_`` in ``params``.
            name_in_params = self.arg_name.replace('-', '_')
        if name_in_params is not None:
            if params.get(name_in_params]:
                # Return the sync strategy object to be used for syncing.
                return self
        return None

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
            if total_seconds(delta) >= 0:
                # Destination is newer than source.
                return True
            else:
                # Destination is older than source, so
                # we have a more recently updated file
                # at the source location.
                return False
        elif cmd == "download":

            if total_seconds(delta) <= 0:
                return True
            else:
                # delta is positive, so the destination
                # is newer than the source.
                return False


class DefaultSyncStrategy(BaseSyncStrategy):

    NAME = 'default'

    def compare_same_name_files(self, src_file, dest_file):
        same_size = self.compare_size(src_file, dest_file)
        same_last_modified_time = self.compare_time(src_file, dest_file)
        should_sync = (not same_size) or (not same_last_modified_time)
        if should_sync:
            LOG.debug("syncing: %s -> %s, size_changed: %s, "
                      "last_modified_time_changed: %s",
                      src_file.src, src_file.dest,
                      not same_size, not same_last_modified_time)
        return should_sync

    def _use_sync_strategy(self, params):
        pass


class SizeOnlySyncStrategy(BaseSyncStrategy):

    NAME = 'size_only'

    ARGUMENT = SIZE_ONLY

    def compare_same_name_files(self, src_file, dest_file):
        same_size = self.compare_size(src_file, dest_file)
        should_sync = not same_size
        if should_sync:
            LOG.debug("syncing: %s -> %s, size_changed: %s",
                      src_file.src, src_file.dest, not same_size)
        return should_sync


class ExactTimestampsSyncStrategy(BaseSyncStrategy):

    NAME = 'exact-timestamps'

    ARGUMENT = EXACT_TIMESTAMPS

    def compare_same_name_files(self, src_file, dest_file):
        same_size = self.compare_size(src_file, dest_file)
        same_last_modified_time = self.compare_time(src_file, dest_file)
        should_sync = (not same_size) or (not same_last_modified_time)
        if should_sync:
            LOG.debug("syncing: %s -> %s, size_changed: %s, "
                      "last_modified_time_changed: %s",
                      src_file.src, src_file.dest,
                      not same_size, not same_last_modified_time)
        return should_sync

    def compare_time(self, src_file, dest_file):
        src_time = src_file.last_update
        dest_time = dest_file.last_update
        delta = dest_time - src_time
        cmd = src_file.operation_name
        if cmd == 'download':
            return total_seconds(delta) == 0
        else:
            return super(SizeOnlySyncStrategy, self).compare_time(src_file,
                                                                  dest_file)
