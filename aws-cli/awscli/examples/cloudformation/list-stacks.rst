**To list AWS CloudFormation stacks**

The following ``list-stacks`` example shows a summary of all stacks that have a status of ``CREATE_COMPLETE``. ::

    aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE

Output::

    {
        "StackSummaries": [
            {
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/myteststack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TemplateDescription": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create a publicly accessible S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
                "StackStatusReason": null,
                "CreationTime": "2013-08-26T03:27:10.190Z",
                "StackName": "myteststack",
                "StackStatus": "CREATE_COMPLETE"
            }
        ]
    }

For more information, see `Managing AWS resources as a single unit with CloudFormation stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html>`__ in the *AWS CloudFormation User Guide*.
