**To apply a stack policy**

The following ``set-stack-policy`` example disables updates for the specified resource in the specified stack. ``stack-policy.json`` is a JSON document that defines the operations allowed on resources in the stack. ::

    aws cloudformation set-stack-policy \
        --stack-name my-stack \
        --stack-policy-body file://stack-policy.json

Contents of ``stack-policy.json``::

    {
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "Update:*",
                "Principal": "*",
                "Resource": "*"
            },
            {
                "Effect": "Deny",
                "Action": "Update:*",
                "Principal": "*",
                "Resource": "LogicalResourceId/bucket"
            }
        ]
    }

This command produces no output.

For more information, see `Prevent updates to stack resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html>`__ in the *AWS CloudFormation User Guide*.
