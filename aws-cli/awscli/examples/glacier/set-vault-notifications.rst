**To configure SNS notifications for a vault**

The following ``set-vault-notifications`` example configures SNS notifications for a vault named ``my-vault``. ::

    aws glacier set-vault-notifications \
        --account-id - \
        --vault-name my-vault \
        --vault-notification-config file://notificationconfig.json

This command produces no output.

``notificationconfig.json`` is a JSON file in the current folder that specifies an SNS topic and the events to publish.

Contents of ``notificationconfig.json``::

    {
        "SNSTopic": "arn:aws:sns:us-west-2:0123456789012:my-vault",
        "Events": ["ArchiveRetrievalCompleted", "InventoryRetrievalCompleted"]
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Configuring Vault Notifications Using the AWS Command Line Interface <https://docs.aws.amazon.com/amazonglacier/latest/dev/configuring-notifications-cli.html>`__ in the *Amazon Glacier Developer Guide*.
