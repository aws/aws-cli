**To decline an invitation to have Guardduty managed by another account in the current region.**

The following ``decline-invitations`` example declines a membership invitation. ::

    aws guardduty decline-invitations \
        --account-ids 123456789012

Output::

    {
        "UnprocessedAccounts": []
    }

For more information, see `Managing GuardDuty accounts by invitation <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_invitations.html>`__ in the *Amazon GuardDuty User Guide*.
