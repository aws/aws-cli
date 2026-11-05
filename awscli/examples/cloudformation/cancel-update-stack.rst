**To cancel a stack update that is in progress**

The following ``cancel-update-stack`` example cancels a stack update on the ``myteststack`` stack. ::

    aws cloudformation cancel-update-stack \
        --stack-name myteststack

This command produces no output.

For more information, see `Cancel a stack update <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-update-cancel.html>`__ in the *AWS CloudFormation User Guide*.
