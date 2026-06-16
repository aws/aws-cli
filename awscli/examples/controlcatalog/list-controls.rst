**Example 1: To list all available controls in the Control Catalog library**

The following ``list-controls`` example lists all available controls in the Control Catalog library.  ::

    aws controlcatalog list-controls

Output::

    {
        "Controls": [
            {
                "Arn": "arn:aws:controlcatalog:::control/m7a5gbdf08wg2o0en010mkng",
                "Aliases": [
                    "BACKUP_RECOVERY_POINT_MINIMUM_RETENTION_CHECK"
                ],
                "Name": "Checks if a recovery point expires no earlier than after the specified period",
                "Description": "Checks if a recovery point expires no earlier than after the specified period. The rule is NON_COMPLIANT if the recovery point has a retention point that is less than the required retention period.",
                "Behavior": "DETECTIVE",
                "Severity": "MEDIUM",
                "ParameterRequirementSummary": "OPTIONAL",
                "Implementation": {
                    "Type": "AWS::Config::ConfigRule",
                    "Identifier": "BACKUP_RECOVERY_POINT_MINIMUM_RETENTION_CHECK"
                },
                "CreateTime": "2021-07-22T19:00:00-05:00",
                "GovernedResources": [],
                "GovernedProviders": [
                    "AWS"
                ]
            },
            {
                "Arn": "arn:aws:controlcatalog:::control/4b0nsxnd47747up54ytdqesxi",
                "Aliases": [
                    "CT.CODEBUILD.PR.3"
                ],
                "Name": "Require any AWS CodeBuild project environment to have logging configured",
                "Description": "This control checks whether AWS CodeBuild projects environment has at least one logging option enabled.",
                "Behavior": "PROACTIVE",
                "Severity": "MEDIUM",
                "ParameterRequirementSummary": "NONE",
                "Implementation": {
                    "Type": "AWS::CloudFormation::Type::HOOK"
                },
                "CreateTime": "2022-11-27T18:00:00-06:00",
                "GovernedProviders": [
                    "AWS"
                ]
            },
            ...
        ]
    }

For more information, see `The AWS Control Tower Control Catalog <https://docs.aws.amazon.com/controltower/latest/controlreference/controls-reference.html>`__ in the *AWS Control Tower User Guide*.

**Example 2: To list specific controls in the Control Catalog library**

The following ``list-controls`` example lists specific controls in the Control Catalog library. ::

    aws controlcatalog list-controls \
        —filter '{"Implementations": {"Types": ["AWS::CloudFormation::Type::HOOK"]}}'

Output::

    {
        "Controls": [
            {
                "Arn": "arn:aws:controlcatalog:::control/4b0nsxnd47747up54ytdqesxi",
                "Aliases": [
                    "CT.CODEBUILD.PR.3"
                ],
                "Name": "Require any AWS CodeBuild project environment to have logging configured",
                "Description": "This control checks whether AWS CodeBuild projects environment has at least one logging option enabled.",
                "Behavior": "PROACTIVE",
                "Severity": "MEDIUM",
                "ParameterRequirementSummary": "NONE",
                "Implementation": {
                    "Type": "AWS::CloudFormation::Type::HOOK"
                },
                "CreateTime": "2022-11-27T18:00:00-06:00",
                "GovernedResources": [
                    "AWS::CodeBuild::Project"
                ],
                "GovernedProviders": [
                    "AWS"
                ]
            },
            {
                "Arn": "arn:aws:controlcatalog:::control/6unff4za5vtu72g08jic7cetr",
                "Aliases": [
                    "CT.RDS.PR.5"
                ],
                "Name": "Require an Amazon RDS database instance to have minor version upgrades configured",
                "Description": "This control checks whether automatic minor version upgrades are enabled for an Amazon RDS database instance.",
                "Behavior": "PROACTIVE",
                "Severity": "HIGH",
                "ParameterRequirementSummary": "NONE",
                "Implementation": {
                    "Type": "AWS::CloudFormation::Type::HOOK"
                },
                "CreateTime": "2022-11-27T18:00:00-06:00",
                "GovernedResources": [
                    "AWS::RDS::DBInstance"
                ],
                "GovernedProviders": [
                    "AWS"
                ]
            },
            ...
        ]
    }

For more information, see `The AWS Control Tower Control Catalog <https://docs.aws.amazon.com/controltower/latest/controlreference/controls-reference.html>`__ in the *AWS Control Tower User Guide*.
