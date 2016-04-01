The following command creates an alias named ``example-alias`` for the customer master key (CMK) identified by key ID ``1234abcd-12ab-34cd-56ef-1234567890ab``.

.. code::

    aws kms create-alias --alias-name alias/example-alias --target-key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Alias names must begin with ``alias/``. Do not use alias names that begin with ``alias/aws``; these are reserved for use by AWS.