**To list instances for a stack**

The following ``list-stack-instances`` example lists the instances created from the specified stack set. ::

    aws cloudformation list-stack-instances \
        --stack-set-name enable-config

The example output includes details about a stack that failed to update due to an error.

Output::

    {
        "Summaries": [
            {
                "StackSetId": "enable-config:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Region": "us-west-2",
                "Account": "123456789111",
                "StackId": "arn:aws:cloudformation:us-west-2:123456789111:stack/StackSet-enable-config-35a6ac50-d9f8-4084-86e4-7da34d5de4c4/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "CURRENT"
            },
            {
                "StackSetId": "enable-config:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Region": "us-west-2",
                "Account": "123456789012",
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/StackSet-enable-config-e6cac20f-xmpl-46e9-8314-53e0d4591532/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "OUTDATED",
                "StatusReason": "ResourceLogicalId:ConfigDeliveryChannel, ResourceType:AWS::Config::DeliveryChannel, ResourceStatusReason:Failed to put delivery channel 'StackSet-enable-config-e6cac20f-xmpl-46e9-8314-53e0d4591532-ConfigDeliveryChannel-1OJWJ7XD59WR0' because the maximum number of delivery channels: 1 is reached. (Service: AmazonConfig; Status Code: 400; Error Code: MaxNumberOfDeliveryChannelsExceededException; Request ID: a1b2c3d4-5678-90ab-cdef-EXAMPLE44444)."
            }
        ]
    }

For more information, see `StackSets concepts <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html>`__ in the *AWS CloudFormation User Guide*.
