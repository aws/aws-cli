**To connect a custom key store**

The following ``connect-custom-key-store`` example reconnects the specified custom key store. You can use a command like this one to connect a custom key store for the first time or to reconnect a key store that was disconnected. ::

    aws kms connect-custom-key-store \
        --custom-key-store-id cks-1234567890abcdef0

This command does not return any output. To verify that the command was effective, use the ``describe-custom-key-stores`` command.

For more information, see `Connecting and Disconnecting a Custom Key Store <https://docs.aws.amazon.com/kms/latest/developerguide/disconnect-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
