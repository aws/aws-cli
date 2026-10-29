**To remove the access policy of a vault**

The following ``delete-vault-access-policy`` example removes the access policy for the specified vault. ::

    aws glacier delete-vault-access-policy \
        --account-id 123456789012 \
        --vault-name example_vault

This command produces no output.

For more information, see `Vault Access Policies <https://docs.aws.amazon.com/amazonglacier/latest/dev/vault-access-policy.html>`__ in the *Amazon Glacier Developer Guide*.
