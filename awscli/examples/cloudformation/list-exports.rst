**To list exports**

The following ``list-exports`` example displays a list of the exports from stacks in the current region. ::

    aws cloudformation list-exports

Output::

    {
        "Exports": [
            {
                "ExportingStackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/private-vpc/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "private-vpc-subnet-a",
                "Value": "subnet-07b410xmplddcfa03"
            },
            {
                "ExportingStackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/private-vpc/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "private-vpc-subnet-b",
                "Value": "subnet-075ed3xmplebd2fb1"
            },
            {
                "ExportingStackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/private-vpc/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "private-vpc-vpcid",
                "Value": "vpc-011d7xmpl100e9841"
            }
        ]
    }

For more information, see `Get exported outputs from a deployed CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html>`__ in the *AWS CloudFormation User Guide*.
