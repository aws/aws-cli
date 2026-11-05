**To wait for CloudFormation to finish updating a stack**

The following ``wait stack-update-complete`` example pauses and resumes only after it can confirm that CloudFormation has updated the specified stack. ::

    aws cloudformation wait stack-update-complete \
        --stack-name "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack-1234/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Update stacks directly <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-direct.html>`__ in the *AWS CloudFormation User Guide*.
