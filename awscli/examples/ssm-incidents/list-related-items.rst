**To list related items**

The following ``list-related-items`` example lists the related items of the specified incident. ::

    aws ssm-incidents list-related-items \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "relatedItems": [
            {
                "identifier": {
                    "type": "OTHER",
                    "value": {
                        "url": "https://console.aws.amazon.com/systems-manager/opsitems/oi-8ef82158e190/workbench?region=us-west-2"
                    }
                },
                "title": "Example related item"
            },
            {
                "identifier": {
                    "type": "PARENT",
                    "value": {
                        "arn": "arn:aws:ssm:us-west-2:123456789012:opsitem/oi-8084126392ac"
                    }
                },
                "title": "parentItem"
            }
        ]
    }

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.