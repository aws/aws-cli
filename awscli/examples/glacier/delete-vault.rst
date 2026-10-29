**To delete a vault**

The following ``delete-vault`` example deletes a vault named ``my-vault``. ::

    aws glacier delete-vault \
        --vault-name my-vault \
        --account-id -

This command produces no output. Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Deleting a Vault in Amazon Glacier Using the AWS Command Line Interface <https://docs.aws.amazon.com/amazonglacier/latest/dev/deleting-vaults-cli.html>`__ in the *Amazon Glacier Developer Guide*.
