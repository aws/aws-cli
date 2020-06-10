**To add accounts as member accounts**

The following ``create-members`` example adds two accounts as member accounts to the requesting master account. ::

    aws securityhub create-members \
        --account-details '[{"AccountId": "123456789111"}, {"AccountId": "123456789222"}]'

Output::

    {
        "UnprocessedAccounts": []
    }

For more information, see `Master and member accounts <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-accounts.html>`__ in the *AWS Security Hub User Guide*.
