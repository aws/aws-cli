**To pause running until the specified role exists**

The following ``wait role-exists`` example pauses and continues only after it can confirm that the specified role exists. ::

    aws iam wait role-exists \
        --role-name MyRole

This command produces no output.