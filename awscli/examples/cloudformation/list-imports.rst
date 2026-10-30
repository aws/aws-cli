**To list imports**

The following ``list-imports`` example lists the stacks that import the specified export. To get the list of available exports, use the ``list-exports`` command. ::

    aws cloudformation list-imports \
        --export-name private-vpc-vpcid

Output::

    {
        "Imports": [
            "my-database-stack"
        ]
    }

For more information, see `Get exported outputs from a deployed CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html>`__ in the *AWS CloudFormation User Guide*.
