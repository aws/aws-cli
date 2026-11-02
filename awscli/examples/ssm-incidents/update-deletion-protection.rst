**To update replication set deletion protection**

The following ``update-deletion-protection`` example updates the deletion protection in your account to protect you from deleting the last Region in your replication set. ::

    aws ssm-incidents update-deletion-protection \
        --arn "arn:aws:ssm-incidents::123456789012:replication-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --deletion-protected

This command produces no output.

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.