The following command creates an alias for a customer master key::

    $ aws kms create-alias --alias-name alias/my-alias --target-key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012

Note that all alias names must begin with ``alias/``.
