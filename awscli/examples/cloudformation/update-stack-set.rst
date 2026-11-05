**To update a stack set**

The following ``update-stack-set`` example adds a tag with the key name ``Owner`` and a value of ``IT`` to the stack instances in the specified stack set. ::

    aws cloudformation update-stack-set \
        --stack-set-name my-stack-set \
        --use-previous-template \
        --tags Key=Owner,Value=IT

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Update CloudFormation StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-update.html>`__ in the *AWS CloudFormation User Guide*.
