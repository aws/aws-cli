**To disconnect a custom key store**

The following ``disconnect-custom-key-store`` example disconnects the specified custom key store. ::

    aws kms disconnect-custom-key-store \
        --custom-key-store-id cks-1234567890abcdef0

This command does not return any output. To verify that the command was effective, use the ``describe-custom-key-stores`` command.

For more information, see `Connecting and Disconnecting a Custom Key Store <https://docs.aws.amazon.com/kms/latest/developerguide/disconnect-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
