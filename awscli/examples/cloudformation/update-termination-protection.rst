**To enable termination protection**

The following ``update-termination-protection`` example enables termination protection on the specified stack. ::

    aws cloudformation update-termination-protection \
        --stack-name my-stack \
        --enable-termination-protection

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Protect CloudFormation stacks from being deleted <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-protect-stacks.html>`__ in the *AWS CloudFormation User Guide*.
