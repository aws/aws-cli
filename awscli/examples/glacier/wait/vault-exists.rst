**To pause until a vault exists***

The following ``wait vault-exists`` example pauses running and continues only after it confirms that the specified vault exists. ::

    aws glacier wait vault-exists \
        --account-id 123456789012 \
        --vault-name example_vault

This command produces no output.

For more information, see `Creating a Vault in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/creating-vaults.html>`__ in the *Amazon Glacier Developer Guide*.
