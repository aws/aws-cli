**To get the notification configuration for a vault**

The following ``get-vault-notifications`` example gets a description of the notification configuration for a vault named ``my-vault``. ::

    aws glacier get-vault-notifications \
        --account-id - \
        --vault-name my-vault

Output::

    {
        "vaultNotificationConfig": {
            "Events": [
                "InventoryRetrievalCompleted",
                "ArchiveRetrievalCompleted"
            ],
            "SNSTopic": "arn:aws:sns:us-west-2:0123456789012:my-vault"
        }
    }

If no notifications have been configured for the vault, an error is returned. Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Configuring Vault Notifications in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/configuring-notifications.html>`__ in the *Amazon Glacier Developer Guide*.
