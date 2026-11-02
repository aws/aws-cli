**To remove an account as the delegated administrator for GuardDuty within your organization**

The following ``disable-organization-admin-account`` example removes an account as the delegated administrator for GuardDuty. ::

    aws guardduty disable-organization-admin-account \
        --admin-account-id 123456789012

This command produces no output.

For more information, see `Managing accounts with AWS organizations <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_organizations.html>`__ in the *GuardDuty User Guide*.