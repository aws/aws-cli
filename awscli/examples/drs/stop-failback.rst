**To stop failback for a recovery instance**

The following ``stop-failback`` example stops the failback process for the specified recovery instance. ::

    aws drs stop-failback \
        --recovery-instance-id s-1234567890abcdef0

This command produces no output.

For more information, see `Performing a failback <https://docs.aws.amazon.com/drs/latest/userguide/failback.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
