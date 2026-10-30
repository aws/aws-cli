**To update an incident record**

The following ``update-incident-record`` example resolves the specified incident. ::

    aws ssm-incidents update-incident-record \
        --arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --status "RESOLVED"

This command produces no output.

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.