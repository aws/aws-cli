**To pause running until the specified role exists**

The following ``wait role-exists`` example pauses and continues only after it can confirm that the specified role exists. ::

    aws iam wait role-exists \
        --role-name MyRole

This command produces no output.

For more information, see `IAM role creation <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html>`__ in the *AWS IAM User Guide*.
