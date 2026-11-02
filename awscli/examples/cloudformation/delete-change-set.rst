**To delete a change set**

The following ``delete-change-set`` example deletes a change set by specifying the change set name and stack name. ::

    aws cloudformation delete-change-set \
        --stack-name my-stack \
        --change-set-name my-change-set

This command produces no output.

The following ``delete-change-set`` example deletes a change set by specifying the full ARN of the change set. ::

    aws cloudformation delete-change-set \
        --change-set-name arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Delete a change set for a CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets-delete.html>`__ in the *AWS CloudFormation User Guide*.
