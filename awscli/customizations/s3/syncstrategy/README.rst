How to make your own sync strategy
=======

1. Make a file with your new sync strategy class.
Make sure the new class inherits from ``BaseSync``

2. Register the new sync strategy class in ``register.py``
To do so, call ``register_sync_strategy`` method from within ``register_sync_strategies`` method.
``register_sync_strategy`` takes two arguments. The first being the class of the new sync strategy
and the second being where to apply the sync strategy also denoted as ``sync_type``.
As to where to apply the sync strategy, you can do it on:
  
-  files that exist both at the source and destination: by denoting ``file_at_src_and_dest``
-  files that exist at the source but not the destination: by denoting ``file_not_at_dest``
-  files that exist at the destination but not the source: by denoting ``file_not_at_src``

``register_sync_strategy`` can only register one sync strategy for one ``sync_type`` at a time.
While a sync operation is being performed, there can only be three sync strategies being used
and there is a strict 1:1 mapping of the three sync strategies being used to the three possible
``sync_type`` such that only one sync strategy can be used for each ``sync_type``.
Note that there are no restrictions on the number of sync strategies registered for a particular
``sync_type``. They just cannot all be performed at once during a sync for that ``sync_type``.

3. Create an argument for the new sync class by filling out the class's global ``ARGUMENT``.
The ``ARGUMENT`` follows the same pattern as a member in ``ARG_TABLE`` from ``BasicCommand``.
It is highly recommended that the argument's ``action`` is to ``store_true`` since the sync strategy
will be used if its argument's representation in the parsed arguments has a value of ``True``.
That way the sync strategy will be used if its  argument is specified in the command line.
If no sync strategies are specified, the sync operation uses default sync strategies for all three types of sync.

4. Implement the ``determine_should_sync`` method in the new class.
Make sure it returns a boolean representing whether a specific operation specified by the
``FileStat`` object, which was received as an argument to the function, should be sent to the
``S3Handler`` which performs all of the operations.

For more information, read the `source <https://github.com/aws/aws-cli/pull/930>`__.
