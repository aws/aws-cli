**To delete an incident record**

The following ``delete-incident-record`` example deletes the specified incident record. ::

    aws ssm-incidents delete-incident-record \
        --arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Incident tracking <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking.html>`__ in the *Incident Manager User Guide*.