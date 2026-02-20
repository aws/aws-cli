**To describe provisioning parameters**

The following ``describe-provisioning-parameters`` example describes provisioning parameters. ::

    aws servicecatalog describe-provisioning-parameters  \
        --product-id prod-cfrfxmraxxxxx \
        --provisioning-artifact-id pa-7wz4cu5cxxxxx \
        --path-id lpv3-y3fnkeslpoevg

Output::

    {
        "ProvisioningArtifactParameters": [
            {
                "ParameterKey": "Size",
                "ParameterType": "String",
                "IsNoEcho": false,
                "ParameterConstraints": {
                    "AllowedValues": []
                }
            }
        ],
        "ConstraintSummaries": [
            {
                "Type": "LAUNCH"
            }
        ],
        "UsageInstructions": [
            {
                "Type": "rules",
                "Value": "{}"
            },
            {
                "Type": "version",
                "Value": "2010-09-09"
            },
            {
                "Type": "launchAsRole",
                "Value": "arn:aws:iam::123456789012:role/NewLaunchRole"
            },
            {
                "Type": "tagUpdateOnProvisionedProduct",
                "Value": "NOT_ALLOWED"
            }
        ],
        "TagOptions": [
            {
                "Key": "Application Name",
                "Values": [
                    "Testing Tag",
                    "Testing Tag Options"
                ]
            }
        ],
        "ProvisioningArtifactPreferences": {},
        "ProvisioningArtifactOutputs": [
            {
                "Key": "pa-7wz4cu5cxxxxx",
                "Description": ""
            }
        ],
        "ProvisioningArtifactOutputKeys": []
    }
