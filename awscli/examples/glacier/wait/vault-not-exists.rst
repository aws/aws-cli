**To pause until a vault no longer exists**

The following ``wait vault-not-exists`` example pauses running and continues only after it confirms that the specified vault doesn't exist. ::

    aws glacier wait vault-not-exists \
        --account-id 123456789012 \
        --vault-name example_vault

This command produces no output.

For more information, see `Deleting a Vault in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/deleting-vaults.html>`__ in the *Amazon Glacier Developer Guide*.
