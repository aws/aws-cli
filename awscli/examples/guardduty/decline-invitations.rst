**To decline an invitation to have Guardduty managed by another account in the current region.**

The following ``decline-invitations`` example declines a membership invitation. ::

    aws guardduty decline-invitations \
        --account-ids 111122223333

Output::

    {
        "UnprocessedAccounts": []
    }

For more information, see `Managing GuardDuty accounts by invitation <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_invitations.html>`__ in the GuardDuty User Guide.
