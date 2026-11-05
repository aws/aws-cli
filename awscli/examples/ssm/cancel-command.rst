**Example 1: To cancel a command for all instances**

The following ``cancel-command`` example attempts to cancel the specified command that is already running for all instances. ::

    aws ssm cancel-command \
        --command-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

**Example 2: To cancel a command for specific instances**

The following ``cancel-command`` example attempts to cancel a command for the specified instance only. ::

    aws ssm cancel-command \
        --command-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --instance-ids "i-02573cafcfEXAMPLE"

This command produces no output.

For more information, see `Canceling a command <https://docs.aws.amazon.com/systems-manager/latest/userguide/cancel-run-command.html>`__ in the *AWS Systems Manager User Guide*.
