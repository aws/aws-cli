**To delete a timeline event**

The following ``delete-timeline-event`` example deletes a custom timeline event from the specified incident record. ::

    aws ssm-incidents delete-timeline-event \
        --event-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

This command produces no output.

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.