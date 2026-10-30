**Example 1: To create a custom timeline event**

The following ``create-timeline-event`` example creates a custom timeline event at the specified time on the specified incident. ::

    aws ssm-incidents create-timeline-event \
        --event-data "\"example timeline event\"" \
        --event-time 2022-10-01T20:30:00.000 \
        --event-type "Custom Event" \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To create a timeline event with an incident note**

The following ``create-timeline-event`` example creates a timeline event that is listed in the 'Incident notes' panel. ::

    aws ssm-incidents create-timeline-event \
        --event-data "\"New Note\"" \
        --event-type "Note" \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Test/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333" \
        --event-time 2023-06-20T12:06:00.000 \
        --event-references '[{"resource":"arn:aws:ssm-incidents::123456789012:incident-record/Test/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"}]'

Output::

    {
        "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
        "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.