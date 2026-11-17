**Example 1: To display a list of objectives from the Control Catalog**

The following ``list-objectives`` example displays a list of control objectives in the Control Catalog. ::

    aws controlcatalog list-objectives

Output::

    {
        "Objectives": [
            {
                "Arn": "arn:aws:controlcatalog:::objective/ad11p1961s8erra9m1EXAMPLE",
                "Name": "Asset inventory management",
                "Description": "This control objective focuses on maintaining an accurate and up-to-date inventory of assets, including hardware, software, and data, to protect organization investments from harm or loss.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            },
            {
                "Arn": "arn:aws:controlcatalog:::objective/90gifwthorhxhxq7m0EXAMPLE",
                "Name": "Asset classification",
                "Description": "This control objective focuses on classifying assets based on their value, sensitivity, and criticality to the organization to manage investment risk and unauthorized access to assets and information.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            }
        ]
    }

For more information, see `Control catalog: control objectives <https://docs.aws.amazon.com/controltower/latest/controlreference/control-catalog-objectives.html>`__ in the *AWS Control Catalog User Guide*.

**Example 2: To display a list of specific objectives filtered by domain**

The following ``list-objectives`` example displays a list of specific control objectives filtered by domain. ::

    aws controlcatalog list-objectives \
        --objective-filter '{"Domains": [{"Arn": "arn:aws:controlcatalog:::domain/33mjpzadrlwo1by3c1EXAMPLE"}]}'

Output::

    {
        "Objectives": [
            {
                "Arn": "arn:aws:controlcatalog:::objective/9l3arklghxiyc6ehikEXAMPLE",
                "Name": "Business continuity",
                "Description": "This control objective focuses on developing and maintaining plans, procedures, and protocols that support an organization's ability to recover critical business functions in the event of a disruption, including backup and recovery and business impact analysis.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/33mjpzadrlwo1by3c1EXAMPLE",
                    "Name": "Business continuity and recovery"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            },
            {
                "Arn": "arn:aws:controlcatalog:::objective/8fub2rjbldjmrseky5EXAMPLE",
                "Name": "Disaster recovery",
                "Description": "This control objective focuses on the steps and technologies necessary to recover critical information resources in the event of a natural disaster, security event and/or incident, and/or system outage and ensure critical business functions can continue.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/33mjpzadrlwo1by3c1EXAMPLE",
                    "Name": "Business continuity and recovery"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            }
        ]
    }

For more information, see `Control catalog: control objectives <https://docs.aws.amazon.com/controltower/latest/controlreference/control-catalog-objectives.html>`__ in the *AWS Control Catalog User Guide*.
