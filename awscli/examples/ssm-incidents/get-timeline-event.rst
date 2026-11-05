**To get details of a timeline event**

The following ``get-timeline-event`` example returns details of the specified timeline event. ::

    aws ssm-incidents get-timeline-event \
        --event-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "event": {
            "eventData": "\"Incident Started\"",
            "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "eventTime": "2021-05-21T18:16:57+00:00",
            "eventType": "Custom Event",
            "eventUpdatedTime": "2021-05-21T18:16:59.944000+00:00",
            "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.