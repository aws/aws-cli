**To initiate the vault locking process**

The following ``initiate-vault-lock`` example installs a vault lock policy on the specified vault and sets the lock state of the vault lock to ``InProgress``. You must complete the process by calling ``complete-vault-lock`` within 24 hours to set the state of the vault lock to ``Locked``. ::

    aws glacier initiate-vault-lock \
        --account-id - \
        --vault-name MyVaultName \
        --policy file://vault_lock_policy.json

Contents of ``vault_lock_policy.json``::

    {"Policy":"{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"Define-vault-lock\",\"Effect\":\"Deny\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789012:root\"},\"Action\":\"glacier:DeleteArchive\",\"Resource\":\"arn:aws:glacier:us-west-2:123456789012:vaults/examplevault\",\"Condition\":{\"NumericLessThanEquals\":{\"glacier:ArchiveAgeinDays\":\"365\"}}}]}"}

Output::

    {
        "lockId": "9QZgEXAMPLEPhvL6xEXAMPLE"
    }

The output is the vault lock ID that you can use to complete the vault lock process.

For more information, see `Initiate Vault Lock (POST lock-policy) <https://docs.aws.amazon.com/amazonglacier/latest/dev/api-InitiateVaultLock.html>`__ in the *Amazon Glacier API Developer Guide*.
