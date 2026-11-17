**To get the evaluation results for an AWS resource**

The following ``get-compliance-details-by-resource`` example returns the evaluation results for each rule with which the EC2 instance ``i-1a2b3c4d`` does not comply. ::

    aws configservice get-compliance-details-by-resource \
        --resource-type AWS::EC2::Instance \
        --resource-id i-1a2b3c4d \
        --compliance-types NON_COMPLIANT

Output::

    {
        "EvaluationResults": [
            {
                "EvaluationResultIdentifier": {
                    "OrderingTimestamp": 1450314635.065,
                    "EvaluationResultQualifier": {
                        "ResourceType": "AWS::EC2::Instance",
                        "ResourceId": "i-1a2b3c4d",
                        "ConfigRuleName": "InstanceTypesAreT2micro"
                    }
                },
                "ResultRecordedTime": 1450314643.288,
                "ConfigRuleInvokedTime": 1450314643.034,
                "ComplianceType": "NON_COMPLIANT"
            },
            {
                "EvaluationResultIdentifier": {
                    "OrderingTimestamp": 1450314635.065,
                    "EvaluationResultQualifier": {
                        "ResourceType": "AWS::EC2::Instance",
                        "ResourceId": "i-1a2b3c4d",
                        "ConfigRuleName": "RequiredTagForEC2Instances"
                    }
                },
                "ResultRecordedTime": 1450314645.261,
                "ConfigRuleInvokedTime": 1450314642.948,
                "ComplianceType": "NON_COMPLIANT"
            }
        ]
    }

For more information, see `Viewing Compliance Information and Evaluation Results for your AWS Resources with AWS Config <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_view-compliance.html>`__ in the *AWS Config Developer Guide*.
