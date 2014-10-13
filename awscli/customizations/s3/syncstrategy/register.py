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
from awscli.customizations.s3.syncstrategy.sizeonly import SizeOnlySync
from awscli.customizations.s3.syncstrategy.exacttimestamps import \
    ExactTimestampsSync
from awscli.customizations.s3.syncstrategy.delete import DeleteSync


def register_sync_strategy(session, strategy_cls,
                           sync_type='file_at_src_and_dest'):
    """Registers a single sync strategy

    :param session: The session that the sync strategy is being registered to.
    :param strategy_cls: The class of the sync strategy to be registered.
    :param sync_type: A string representing when to perform the sync strategy.
        See ``__init__`` method of ``BaseSyncStrategy`` for possible options.
    """
    strategy = strategy_cls(sync_type)
    strategy.register_strategy(session)


def register_sync_strategies(command_table, session, **kwargs):
    """Registers the different sync strategies.

    To register a sync strategy add
    ``register_sync_strategy(session, YourSyncStrategyClass, sync_type)``
    to the list of registered strategies in this function.
    """

    # Register the size only sync strategy.
    register_sync_strategy(session, SizeOnlySync)

    # Register the exact timestamps sync strategy.
    register_sync_strategy(session, ExactTimestampsSync)

    # Register the delete sync strategy.
    register_sync_strategy(session, DeleteSync, 'file_not_at_src')

    # Register additional sync strategies here...
