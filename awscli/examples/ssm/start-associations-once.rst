**To run an association immediately and only one time**

The following ``start-associations-once`` example run the specified association immediately and only once. There is no output if the command succeeds. ::

    aws ssm start-associations-once \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Viewing association histories <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-history.html>`__ in the *AWS Systems Manager User Guide*.