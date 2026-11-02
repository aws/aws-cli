**To list change sets**

The following ``list-change-sets`` example displays a list of the pending change sets for the specified stack. ::

    aws cloudformation list-change-sets \
        --stack-name my-stack

Output::

    {
        "Summaries": [
            {
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "StackName": "my-stack",
                "ChangeSetId": "arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ChangeSetName": "my-change-set",
                "ExecutionStatus": "AVAILABLE",
                "Status": "CREATE_COMPLETE",
                "CreationTime": "2019-10-02T05:38:54.297Z"
            }
        ]
    }

For more information, see `Update CloudFormation stacks using change sets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html>`__ in the *AWS CloudFormation User Guide*.
