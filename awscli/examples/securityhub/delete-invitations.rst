**To delete an invitation to be a member account**

The following ``delete-invitations`` example deletes an invitation to be a member account for the specified master account. The member account is the requesting account. ::

    aws securityhub delete-invitations \
        --account-ids "123456789012"

Output::

    {
        "UnprocessedAccounts": []
    }

For more information, see `Master and member accounts <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-accounts.html>`__ in the *AWS Security Hub User Guide*.
