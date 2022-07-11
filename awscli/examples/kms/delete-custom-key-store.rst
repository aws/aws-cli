**To delete a custom key store**

The following ``delete-custom-key-store`` example deletes the specified custom key store. This command doesn't have any effect on the associated CloudHSM cluster.

**NOTE:** Before you can delete a custom key store, you must schedule the deletion of all KMS keys in the custom key store and then wait for those KMS keys to be deleted. Then, you must disconnect the custom key store. ::

    delete-custom-key-store \
        --custom-key-store-id cks-1234567890abcdef0

This command does not return any output. To verify that the custom key store is deleted, use the ``describe-custom-key-stores`` command.

For more information, see `Deleting a custom key store <https://docs.aws.amazon.com/kms/latest/developerguide/delete-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
