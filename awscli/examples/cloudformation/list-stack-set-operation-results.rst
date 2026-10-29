**To list stack set operation results**

The following ``list-stack-set-operation-results`` example displays the results of an update operation on instances in the specified stack set. ::

    aws cloudformation list-stack-set-operation-results \
        --stack-set-name enable-config \
        --operation-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Summaries": [
            {
                "Account": "123456789111",
                "Region": "us-west-2",
                "Status": "SUCCEEDED",
                "AccountGateResult": {
                    "Status": "SKIPPED",
                    "StatusReason": "Function not found: arn:aws:lambda:us-west-2:123456789111:function:AWSCloudFormationStackSetAccountGate"
                }
            },
            {
                "Account": "123456789222",
                "Region": "us-west-2",
                "Status": "CANCELLED",
                "StatusReason": "Cancelled since failure tolerance has exceeded"
            }
        ]
    }

**Note:** The ``SKIPPED`` status for ``AccountGateResult`` is expected for successful operations unless you create an account gate function.

For more information, see `StackSet operations <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html#stacksets-concepts-ops>`__ in the *AWS CloudFormation User Guide*.
