**Example 1: To add an AWS managed Config rule**

The following ``put-config-rule`` example provides JSON code to add an AWS managed Config rule. ::

    aws configservice put-config-rule \
        --config-rule file://RequiredTagsForEC2Instances.json

``RequiredTagsForEC2Instances.json`` is a JSON file that contains the rule configuration.

Contents of ``RequiredTagsForEC2Instances.json``::

    {
        "ConfigRuleName": "RequiredTagsForEC2Instances",
        "Description": "Checks whether the CostCenter and Owner tags are applied to EC2 instances.",
        "Scope": {
            "ComplianceResourceTypes": [
                "AWS::EC2::Instance"
            ]
        },
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "REQUIRED_TAGS"
        },
        "InputParameters": "{\"tag1Key\":\"CostCenter\",\"tag2Key\":\"Owner\"}"
    }

For the ``ComplianceResourceTypes`` attribute, this JSON code limits the scope to resources of the ``AWS::EC2::Instance`` type, so AWS Config will evaluate only EC2 instances against the rule. Because the rule is a managed rule, the ``Owner`` attribute is set to ``AWS``, and the ``SourceIdentifier`` attribute is set to the rule identifier, ``REQUIRED_TAGS``. For the ``InputParameters`` attribute, the tag keys that the rule requires, ``CostCenter`` and ``Owner``, are specified.

This command produces no output. To verify the rule configuration, run the `describe-config-rules <https://docs.aws.amazon.com/cli/latest/reference/configservice/describe-config-rules.html>`__ command, and specify the rule name.

For more information, see `AWS Config Managed Rules <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_use-managed-rules.html>`__ in the *AWS Config Developer Guide*.

**Example 2: To add a customer managed Config rule**

The following ``put-config-rule`` example provides JSON code to add a customer managed Config rule. ::

    aws configservice put-config-rule \
        --config-rule file://InstanceTypesAreT2micro.json

``InstanceTypesAreT2micro.json`` is a JSON file that contains the rule configuration.

Contents of ``InstanceTypesAreT2micro.json``::

    {
        "ConfigRuleName": "InstanceTypesAreT2micro",
        "Description": "Evaluates whether EC2 instances are the t2.micro type.",
        "Scope": {
            "ComplianceResourceTypes": [
                "AWS::EC2::Instance"
            ]
        },
        "Source": {
            "Owner": "CUSTOM_LAMBDA",
            "SourceIdentifier": "arn:aws:lambda:us-west-2:123456789012:function:InstanceTypeCheck",
            "SourceDetails": [
                {
                    "EventSource": "aws.config",
                    "MessageType": "ConfigurationItemChangeNotification"
                }
            ]
        },
        "InputParameters": "{\"desiredInstanceType\":\"t2.micro\"}"
    }

For the ``ComplianceResourceTypes`` attribute, this JSON code limits the scope to resources of the ``AWS::EC2::Instance`` type, so AWS Config will evaluate only EC2 instances against the rule. Because this rule is a customer managed rule, the ``Owner`` attribute is set to ``CUSTOM_LAMBDA``, and the ``SourceIdentifier`` attribute is set to the ARN of the AWS Lambda function. The ``SourceDetails`` object is required. The parameters that are specified for the ``InputParameters`` attribute are passed to the AWS Lambda function when AWS Config invokes it to evaluate resources against the rule.

This command produces no output. To verify the rule configuration, run the `describe-config-rules <https://docs.aws.amazon.com/cli/latest/reference/configservice/describe-config-rules.html>`__ command, and specify the rule name.

For more information, see `AWS Config Custom Rules <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules.html>`__ in the *AWS Config Developer Guide*.
