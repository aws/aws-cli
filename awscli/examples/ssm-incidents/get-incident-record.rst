**To get an incident record**

The following ``get-incident-record`` example gets details about the specified incident record. ::

    aws ssm-incidents get-incident-record \
        --arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "incidentRecord": {
            "arn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "automationExecutions": [],
            "creationTime": "2021-05-21T18:16:57.579000+00:00",
            "dedupeString": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "impact": 5,
            "incidentRecordSource": {
                "createdBy": "arn:aws:iam::123456789012:user/draliatp",
                "invokedBy": "arn:aws:iam::123456789012:user/draliatp",
                "source": "aws.ssm-incidents.custom"
            },
            "lastModifiedBy": "arn:aws:iam::123456789012:user/draliatp",
            "lastModifiedTime": "2021-05-21T18:16:59.149000+00:00",
            "notificationTargets": [],
            "status": "OPEN",
            "title": "Example-Incident"
        }
    }

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.