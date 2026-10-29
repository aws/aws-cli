**To list timeline events of an incident**

The following ``list-timeline-events`` example lists the timeline events of the specified incident. ::

    aws ssm-incidents list-timeline-events \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "eventSummaries": [
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "eventTime": "2021-05-21T22:36:13.766000+00:00",
                "eventType": "SSM Incident Record Update",
                "eventUpdatedTime": "2021-05-21T22:36:13.766000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "eventTime": "2021-05-21T18:58:46.443000+00:00",
                "eventType": "SSM Incident Record Update",
                "eventUpdatedTime": "2021-05-21T18:58:46.443000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "eventTime": "2021-05-21T18:16:59.149000+00:00",
                "eventType": "SSM Incident Record Update",
                "eventUpdatedTime": "2021-05-21T18:16:59.149000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "eventTime": "2021-05-21T18:16:58+00:00",
                "eventType": "SSM Automation Execution Start Failure for Incident",
                "eventUpdatedTime": "2021-05-21T18:16:58.689000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "eventTime": "2021-05-21T18:16:57+00:00",
                "eventType": "Custom Event",
                "eventUpdatedTime": "2021-05-21T18:16:59.944000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "eventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "eventTime": "2020-10-01T20:30:00+00:00",
                "eventType": "Custom Event",
                "eventUpdatedTime": "2021-05-21T22:28:26.299000+00:00",
                "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.