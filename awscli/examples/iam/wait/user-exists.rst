**To pause running until the specified user exists**

The following ``wait user-exists`` example pauses and continues only after it can confirm that the specified user exists. ::

    aws iam wait user-exists \
        --user-name marcia

This command produces no output.

For more information, see `Create an IAM user in your AWS account <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html>`__ in the *AWS IAM User Guide*.
