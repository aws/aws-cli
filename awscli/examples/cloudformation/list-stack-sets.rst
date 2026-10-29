**To list stack sets**

The following ``list-stack-sets`` example displays the list of stack sets in the current region and account. ::

    aws cloudformation list-stack-sets

Output::

    {
        "Summaries": [
            {
                "StackSetName": "enable-config",
                "StackSetId": "enable-config:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description": "Enable AWS Config",
                "Status": "ACTIVE"
            }
        ]
    }

For more information, see `Managing stacks across accounts and Regions with StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html>`__ in the *AWS CloudFormation User Guide*.
