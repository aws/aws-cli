**To describe a vault**

The following ``describe-vault`` example retrieves data about a vault named ``my-vault``. ::

    aws glacier describe-vault \
        --vault-name my-vault \
        --account-id -

Output::

    {
        "VaultARN": "arn:aws:glacier:us-west-2:123456789012:vaults/my-vault",
        "VaultName": "my-vault",
        "CreationDate": "2015-07-17T19:22:31.123Z",
        "LastInventoryDate": "2015-07-18T03:41:12.456Z",
        "NumberOfArchives": 1,
        "SizeInBytes": 3178496
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Retrieving Vault Metadata in Amazon Glacier Using the AWS Command Line Interface <https://docs.aws.amazon.com/amazonglacier/latest/dev/retrieving-vault-info-cli.html>`__ in the *Amazon Glacier Developer Guide*.
