**To list stack set operations**

The following ``list-stack-set-operations`` example displays the list of the most recent operations on the specified stack set. ::

    aws cloudformation list-stack-set-operations \
        --stack-set-name my-stack-set

Output::

    {
        "Summaries": [
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Action": "UPDATE",
                "Status": "SUCCEEDED",
                "CreationTimestamp": "2019-10-03T16:28:44.377Z",
                "EndTimestamp": "2019-10-03T16:42:08.607Z"
            },
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Action": "UPDATE",
                "Status": "FAILED",
                "CreationTimestamp": "2019-10-03T15:43:53.916Z",
                "EndTimestamp": "2019-10-03T15:45:58.925Z"
            }
        ]
    }

For more information, see `StackSets concepts <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html>`__ in the *AWS CloudFormation User Guide*.
