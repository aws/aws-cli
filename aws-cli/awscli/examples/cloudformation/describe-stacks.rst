**To describe AWS CloudFormation stacks**

The following ``describe-stacks`` example shows summary information for the ``myteststack`` stack. ::

    aws cloudformation describe-stacks \
        --stack-name myteststack

Output::

    {
        "Stacks":  [
            {
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/myteststack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create a publicly accessible S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
                "Tags": [],
                "Outputs": [
                    {
                        "Description": "Name of S3 bucket to hold website content",
                        "OutputKey": "BucketName",
                        "OutputValue": "myteststack-s3bucket-jssofi1zie2w"
                    }
                ],
                "StackStatusReason": null,
                "CreationTime": "2013-08-23T01:02:15.422Z",
                "Capabilities": [],
                "StackName": "myteststack",
                "StackStatus": "CREATE_COMPLETE",
                "DisableRollback": false
            }
        ]
    }

For more information, see `Managing AWS resources as a single unit with CloudFormation stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html>`__ in the *AWS CloudFormation User Guide*.
