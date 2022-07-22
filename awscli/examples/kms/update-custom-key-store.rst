**To edit custom key store settings**

The following ``update-custom-key-store`` example provides the current password for the ``kmsuser`` in the CloudHSM cluster that is associated with the specified key store. This command doesn't change the ``kmsuser`` password. It just tells AWS KMS the current password. If KMS doesn't have the current ``kmsuser`` password, it cannot connect to the custom key store.

**NOTE:** Before updating the custom key store, you must disconnect it. Use the ``disconnect-custom-key-store`` command. After the command completes, you can reconnect the custom key store. Use the ``connect-custom-key-store`` command. ::

    aws kms update-custom-key-store \
        --custom-key-store-id cks-1234567890abcdef0 \
        --key-store-password ExamplePassword

This command does not return any output. To verify that the password change was effective, connect the custom key store.

For more information, see `Editing custom key store settings <https://docs.aws.amazon.com/kms/latest/developerguide/update-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
