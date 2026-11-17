**Example 1: To display all common controls from the AWS Control Catalog**

The following ``list-common-controls`` example displays all common controls from the AWS Control Catalog. ::

    aws controlcatalog list-common-controls

Output::

    {
        "CommonControls": [
            {
                "Arn": "arn:aws:controlcatalog:::common-control/d4s7ik8fgv8082v3x3EXAMPLE",
                "Name": "Asset inventory reconciliation and audit",
                "Description": "Reconcile the organization's asset inventory with other data sources, and conduct asset audits to verify the accuracy of the asset inventory.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "Objective": {
                    "Arn": "arn:aws:controlcatalog:::objective/ad11p1961s8erra9m1EXAMPLE",
                    "Name": "Asset inventory management"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            },
            {
                "Arn": "arn:aws:controlcatalog:::common-control/7encqm6cfsw704eoahEXAMPLE",
                "Name": "Asset valuation",
                "Description": "Assign a value to assets based on their cost, replacement value, or other relevant factors.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "Objective": {
                    "Arn": "arn:aws:controlcatalog:::objective/90gifwthorhxhxq7m0EXAMPLE",
                    "Name": "Asset classification"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            }
        ]
    }

For more information, see `About common controls <https://docs.aws.amazon.com/controltower/latest/controlreference/common-controls-list.html>`__ in the *AWS Control Tower User Guide*.

**Example 2: To display common controls that have a specific objective**

The following ``list-common-controls`` example displays common controls that have a specific objective. ::

    aws controlcatalog list-common-controls \
        --common-control-filter '{"Objectives": [{"Arn": "arn:aws:controlcatalog:::objective/ad11p1961s8erra9m1EXAMPLE"}]}'

Output::

    {
        "CommonControls": [
            {
                "Arn": "arn:aws:controlcatalog:::common-control/d4s7ik8fgv8082v3x3EXAMPLE",
                "Name": "Asset inventory reconciliation and audit",
                "Description": "Reconcile the organization's asset inventory with other data sources, and conduct asset audits to verify the accuracy of the asset inventory.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "Objective": {
                    "Arn": "arn:aws:controlcatalog:::objective/ad11p1961s8erra9m1EXAMPLE",
                    "Name": "Asset inventory management"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            },
            {
                "Arn": "arn:aws:controlcatalog:::common-control/1ukpmkewk4i92tjmhsEXAMPLE",
                "Name": "Inventory of authorized assets and automated discovery",
                "Description": "Maintain an asset inventory of organization authorized and existing hardware, software, and media. Where possible, utilize automated tools to facilitate the discovery and ongoing tracking of such assets.",
                "Domain": {
                    "Arn": "arn:aws:controlcatalog:::domain/d4msesd9vvmzmmuvlvEXAMPLE",
                    "Name": "Asset management"
                },
                "Objective": {
                    "Arn": "arn:aws:controlcatalog:::objective/ad11p1961s8erra9m1EXAMPLE",
                    "Name": "Asset inventory management"
                },
                "CreateTime": "2024-03-12T19:00:00-05:00",
                "LastUpdateTime": "2024-03-12T19:00:00-05:00"
            }
        ]
    }

For more information, see `About common controls <https://docs.aws.amazon.com/controltower/latest/controlreference/common-controls-list.html>`__ in the *AWS Control Tower User Guide*.
