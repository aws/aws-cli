**To update a timeline event**

The following ``update-timeline-event`` example updates the time that the event occurred. ::

    aws ssm-incidents update-timeline-event \
        --event-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222" \
        --event-time "2021-05-21T18:10:57+00:00"

This command produces no output.

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.