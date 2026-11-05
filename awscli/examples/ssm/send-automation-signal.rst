**To send a signal to an automation execution**

The following ``send-automation-signal`` example sends an Approve signal to an Automation execution. ::

    aws ssm send-automation-signal \
        --automation-execution-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --signal-type "Approve"

This command produces no output.

For more information, see `Running an Automation Workflow with Approvers <https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-working-executing-approval.html>`__ in the *AWS Systems Manager User Guide*.
