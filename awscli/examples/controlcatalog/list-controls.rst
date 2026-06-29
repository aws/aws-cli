**Example 1: To retrieve a list of available controls in the Control Catalog library**

The following ``list-controls`` example retrieves a list of available controls in the Control Catalog library. ::

    aws controlcatalog list-controls

Output::

    {
        "Controls": [
            {
                "Arn": "arn:aws:controlcatalog:::control/m7a5gbdf08wg2o0enEXAMPLE",
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
                "Arn": "arn:aws:controlcatalog:::control/4b0nsxnd47747up54yEXAMPLE",
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
            }
        ]
    }

For more information, see `The AWS Control Tower Control Catalog <https://docs.aws.amazon.com/controltower/latest/controlreference/controls-reference.html>`__ in the *AWS Control Tower User Guide*.

**Example 2: To retrieve a list of available controls filtered by identifier and implementation type**

The following ``list-controls`` example retrieves a list of available controls filtered by identifier and implementation type. ::

    aws controlcatalog list-controls \
        --filter '{"Implementations":{"Identifiers":["CODEPIPELINE_DEPLOYMENT_COUNT_CHECK"], "Types":["AWS::Config::ConfigRule"]}}'

Output::

    {
        "Controls": [
            {
                "Arn": "arn:aws:controlcatalog:::control/8k65jh499ji8qa5tb3EXAMPLE",
                "Aliases": [
                    "CONFIG.CODEPIPELINE.DT.1"
                ],
                "Name": "Checks if the first deployment stage of AWS CodePipeline performs more than one deployment",
                "Description": "Checks if the first deployment stage of AWS CodePipeline performs more than one deployment. Optionally checks if each of the subsequent remaining stages deploy to more than the specified number of deployments (deploymentLimit).",
                "Behavior": "DETECTIVE",
                "Severity": "MEDIUM",
                "ParameterRequirementSummary": "OPTIONAL",
                "Implementation": {
                    "Type": "AWS::Config::ConfigRule",
                    "Identifier": "CODEPIPELINE_DEPLOYMENT_COUNT_CHECK"
                },
                "CreateTime": "2018-10-31T19:00:00-05:00",
                "GovernedResources": [
                    "AWS::CodePipeline::Pipeline"
                ],
                "GovernedProviders": [
                    "AWS"
                ]
            }
        ]
    }

For more information, see `The AWS Control Tower Control Catalog <https://docs.aws.amazon.com/controltower/latest/controlreference/controls-reference.html>`__ in the *AWS Control Tower User Guide*.
