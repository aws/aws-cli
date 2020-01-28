**To list versions of a type**

The following ``list-type-versions`` example displays summary information of each version of the specified type whose status is ``LIVE``. ::

    aws cloudformation list-type-versions \
        --type RESOURCE \
        --type-name My::Logs::LogGroup \
        --deprecated-status LIVE

Output::

    {
        "TypeVersionSummaries": [
            {
                "Description": "Customized resource derived from AWS::Logs::LogGroup",
                "TimeCreated": "2019-12-03T23:29:33.321Z",
                "TypeName": "My::Logs::LogGroup",
                "VersionId": "00000001",
                "Type": "RESOURCE",
                "Arn": "arn:aws:cloudformation:us-west-2:123456789012:type/resource/My-Logs-LogGroup/00000001"
            },
            {
                "Description": "Customized resource derived from AWS::Logs::LogGroup",
                "TimeCreated": "2019-12-04T06:58:14.902Z",
                "TypeName": "My::Logs::LogGroup",
                "VersionId": "00000002",
                "Type": "RESOURCE",
                "Arn": "arn:aws:cloudformation:us-west-2:123456789012:type/resource/My-Logs-LogGroup/00000002"
            }
        ]
    }

For more information, see `Using the CloudFormation Registry <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html>`__ in the *AWS CloudFormation Users Guide*.
