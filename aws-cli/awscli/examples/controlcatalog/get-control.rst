**To show information about an individual control**

The following ``get-control`` example shows information about an individual control. ::

    aws controlcatalog get-control \
        --control-arn arn:aws:controlcatalog:::control/cwlixshc8c8mw9qiwdEXAMPLE

Output::

    {
        "Arn": "arn:aws:controlcatalog:::control/cwlixshc8c8mw9qiwdEXAMPLE",
        "Aliases": [
            "AWS-GR_REGION_DENY"
        ],
        "Name": "Deny access to AWS based on the requested AWS Region for the landing zone",
        "Description": "Disallows access to unlisted operations in global and regional services outside of the specified Regions for the landing zone.",
        "Behavior": "PREVENTIVE",
        "Severity": "MEDIUM",
        "RegionConfiguration": {
            "Scope": "GLOBAL"
        },
        "Implementation": {
            "Type": "AWS::Organizations::Policy::SERVICE_CONTROL_POLICY"
        },
        "ParameterRequirementSummary": "NONE",
        "Parameters": [],
        "CreateTime": "2022-07-25T19:00:00-05:00",
        "GovernedResources": [],
        "GovernedProviders": [
            "AWS"
        ]
    }

For more information, see `The AWS Control Tower Control Catalog <https://docs.aws.amazon.com/controltower/latest/controlreference/controls-reference.html>`__ in the *AWS Control Tower User Guide*.
