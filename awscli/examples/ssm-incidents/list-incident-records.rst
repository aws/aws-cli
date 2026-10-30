**To list incident records**

The following ``list-incident-records`` example lists the incident records in your Amazon Web Services account. ::

    aws ssm-incidents list-incident-records

Output::

    {
        "incidentRecordSummaries": [
            {
                "arn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "creationTime": "2021-05-21T18:16:57.579000+00:00",
                "impact": 5,
                "incidentRecordSource": {
                    "createdBy": "arn:aws:iam::123456789012:user/draliatp",
                    "invokedBy": "arn:aws:iam::123456789012:user/draliatp",
                    "source": "aws.ssm-incidents.custom"
                },
                "status": "OPEN",
                "title": "Example-Incident"
            }
        ]
    }

For more information, see `Incident list <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-list.html>`__ in the *Incident Manager User Guide*.