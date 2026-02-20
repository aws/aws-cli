**To describe a product**

The following ``describe-product`` example describes a product. ::

    aws servicecatalog describe-product  \
        --id prod-dybl43puxxxxx

Output::

    {
        "ProductViewSummary": {
            "Id": "prodview-vkvy2kum5ojky",
            "ProductId": "prod-dybl43puxxxxx",
            "Name": "ec2-test",
            "Owner": "user",
            "ShortDescription": "",
            "Type": "CLOUD_FORMATION_TEMPLATE",
            "Distributor": "",
            "HasDefaultPath": false,
            "SupportEmail": "",
            "SupportDescription": "",
            "SupportUrl": ""
        },
        "ProvisioningArtifacts": [
            {
                "Id": "pa-j7fs6ybztfwm6",
                "Name": "v2",
                "Description": "",
                "CreatedTime": "2021-07-16T15:20:24-05:00",
                "Guidance": "DEFAULT"
            },
            {
                "Id": "pa-s6z7i2nivoxtm",
                "Description": "Create EC2 and KMS",
                "CreatedTime": "2024-06-13T18:27:54-05:00",
                "Guidance": "DEFAULT"
            },
            {
                "Id": "pa-6573v3blon27u",
                "Name": "v3",
                "CreatedTime": "2024-06-13T18:45:14-05:00",
                "Guidance": "DEFAULT"
            }
        ],
        "Budgets": [],
        "LaunchPaths": [
            {
                "Id": "lpv3-y3fnkeslpoevg",
                "Name": "TestPort"
            }
        ]
    }
