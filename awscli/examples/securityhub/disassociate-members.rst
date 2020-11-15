**To disassociate member accounts**

The following ``disassociate-members`` example disassociates the specified member accounts from the requesting master account. ::

    aws securityhub disassociate-members  \
        --account-ids "123456789111" "123456789222"

This command produces no output.

For more information, see `Master and member accounts <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-accounts.html>`__ in the *AWS Security Hub User Guide*.
