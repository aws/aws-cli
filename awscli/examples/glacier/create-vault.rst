**To create a vault**

The following ``create-vault`` example creates a new vault named ``my-vault``. ::

    aws glacier create-vault \
        --vault-name my-vault \
        --account-id -

Output::

    {
        "location": "/123456789012/vaults/my-vault"
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Creating a Vault in Amazon Glacier Using the AWS Command Line Interface <https://docs.aws.amazon.com/amazonglacier/latest/dev/creating-vaults-cli.html>`__ in the *Amazon Glacier Developer Guide*.
