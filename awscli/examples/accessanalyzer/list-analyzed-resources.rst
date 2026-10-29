**To list the available widgets**

The following ``list-analyzed-resources`` example lists the available widgets in your AWS account. ::

    aws accessanalyzer list-analyzed-resources \
        --analyzer-arn arn:aws:access-analyzer:us-west-2:123456789012:analyzer/ConsoleAnalyzer-account \
        --resource-type AWS::IAM::Role

Output::

    {
        "analyzedResources": [
            {
                "resourceArn": "arn:aws:sns:us-west-2:123456789012:Validation-Email",
                "resourceOwnerAccount": "123456789012",
                "resourceType": "AWS::SNS::Topic"
            },
            {
                "resourceArn": "arn:aws:sns:us-west-2:123456789012:admin-alerts",
                "resourceOwnerAccount": "123456789012",
                "resourceType": "AWS::SNS::Topic"
            },
            {
                "resourceArn": "arn:aws:sns:us-west-2:123456789012:config-topic",
                "resourceOwnerAccount": "123456789012",
                "resourceType": "AWS::SNS::Topic"
            },
            {
                "resourceArn": "arn:aws:sns:us-west-2:123456789012:inspector-topic",
                "resourceOwnerAccount": "123456789012",
                "resourceType": "AWS::SNS::Topic"
            }
        ]
    }

For more information, see `Using AWS Identity and Access Management Access Analyzer <https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html>`__ in the *AWS IAM User Guide*.