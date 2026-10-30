**To execute a change set**

The following ``execute-change-set`` example executes a change set specified by change set name and stack name. ::

    aws cloudformation execute-change-set \
        --change-set-name my-change-set \
        --stack-name my-stack

This command produces no output.

The following ``execute-change-set`` example executes a change set specified by the full ARN of the change set. ::

    aws cloudformation execute-change-set \
        --change-set-name arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Execute a change set for a CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets-execute.html>`__ in the *AWS CloudFormation User Guide*.
