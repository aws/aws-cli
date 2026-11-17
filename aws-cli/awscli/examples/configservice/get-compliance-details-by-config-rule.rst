**To get the evaluation results for an AWS Config rule**

The following ``get-compliance-details-by-config-rule`` example returns the evaluation results for all of the resources that don't comply with an AWS Config rule named ``InstanceTypesAreT2micro``. ::

    aws configservice get-compliance-details-by-config-rule \
        --config-rule-name InstanceTypesAreT2micro \
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
                "ResultRecordedTime": 1450314645.261,
                "ConfigRuleInvokedTime": 1450314642.948,
                "ComplianceType": "NON_COMPLIANT"
            },
            {
                "EvaluationResultIdentifier": {
                    "OrderingTimestamp": 1450314635.065,
                    "EvaluationResultQualifier": {
                        "ResourceType": "AWS::EC2::Instance",
                        "ResourceId": "i-2a2b3c4d",
                        "ConfigRuleName": "InstanceTypesAreT2micro"
                    }
                },
                "ResultRecordedTime": 1450314645.18,
                "ConfigRuleInvokedTime": 1450314642.902,
                "ComplianceType": "NON_COMPLIANT"
            },
            {
                "EvaluationResultIdentifier": {
                    "OrderingTimestamp": 1450314635.065,
                    "EvaluationResultQualifier": {
                        "ResourceType": "AWS::EC2::Instance",
                        "ResourceId": "i-3a2b3c4d",
                        "ConfigRuleName": "InstanceTypesAreT2micro"
                    }
                },
                "ResultRecordedTime": 1450314643.346,
                "ConfigRuleInvokedTime": 1450314643.124,
                "ComplianceType": "NON_COMPLIANT"
            }
        ]
    }

For more information, see `Viewing Compliance Information and Evaluation Results for your AWS Resources with AWS Config <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_view-compliance.html>`__ in the *AWS Config Developer Guide*.
