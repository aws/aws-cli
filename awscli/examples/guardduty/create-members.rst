**To associate a new member with your GuardDuty master account in the current region.**

The following ``create-members`` example associates member accounts to be managed by the current account as the GuardDuty master. ::

    aws guardduty create-members \
        --detector-id b6b992d6d2f48e64bc59180bfexample \
        --account-details AccountId=123456789111,Email=first+member@example.com AccountId=123456789222 ,Email=another+member@example.com

Output::

    {
        "UnprocessedAccounts": []
    }

For more information, see `Managing multiple accounts in Amazon GuardDuty <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_accounts.html>`__ in the *Amazon GuardDuty User Guide*.
