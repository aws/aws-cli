**To show a list of domains from the Control Catalog**

The following ``list-domains`` example shows a list of domains from the Control Catalog. ::

    aws controlcatalog list-domains

Output::

    {
        "Domains": [
            {
                "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                "Name": "Asset management",
                "Description": "This control domain focuses on asset management and the systematic tracking and maintenance of physical or digital assets throughout their lifecycle, including acquisition, utilization, and disposal. This reduces risks related to accidents, malfunctions, and other issues that may cause damage to property or harm to people.",
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            },
            {
                "Arn": "arn:aws:controlcatalog:::domain/33mjpzadrlwo1by3c1EXAMPLE",
                "Name": "Business continuity and recovery",
                "Description": "This control domain focuses on planning and preparation of procedures and resources to ensure the continued operation of critical business functions in the event of a disruption, and to facilitate the recovery of normal operations afterwards.",
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            }
        ]
    }

For more information, see `Ontology overview <https://docs.aws.amazon.com/controlcatalog/latest/userguide/ontology-overview.html>`__ in the *AWS Control Catalog User Guide*.