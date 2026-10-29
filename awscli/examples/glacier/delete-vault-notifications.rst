**To remove the SNS notifications for a vault**

The following ``delete-vault-notifications`` example removes notifications sent by Amazon Simple Notification Service (Amazon SNS) for the specified vault. ::

    aws glacier delete-vault-notifications \
        --account-id 123456789012 \
        --vault-name example_vault

This command produces no output.

For more information, see `Configuring Vault Notifications in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/configuring-notifications.html>`__ in the *Amazon Glacier Developer Guide*.
