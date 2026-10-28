**To configure SNS notifications for a vault**

The following ``set-vault-notifications`` example configures SNS notifications for a vault named ``my-vault``. This command produces no output. ::

    aws glacier set-vault-notifications \
        --account-id - \
        --vault-name my-vault \
        --vault-notification-config file://notificationconfig.json

``notificationconfig.json`` is a JSON file in the current folder that specifies an SNS topic and the events to publish.

Contents of ``notificationconfig.json``::

    {
        "SNSTopic": "arn:aws:sns:us-west-2:0123456789012:my-vault",
        "Events": ["ArchiveRetrievalCompleted", "InventoryRetrievalCompleted"]
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.