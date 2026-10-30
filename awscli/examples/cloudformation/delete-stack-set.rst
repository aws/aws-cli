**To delete a stack set**

The following ``delete-stack-set`` example deletes the specified empty stack set. The stack set must be empty. ::

    aws cloudformation delete-stack-set \
        --stack-set-name my-stack-set

This command produces no output.

To delete instances from the stack set, use the ``delete-stack-instances`` command.

For more information, see `Delete CloudFormation StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-delete.html>`__ in the *AWS CloudFormation User Guide*.
