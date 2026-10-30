**To list the AWS IoT role aliases in your AWS account**

The following ``list-role-aliases`` example lists the AWS IoT role aliases in your AWS account. ::

    aws iot list-role-aliases

Output::

    {
        "roleAliases": [
            "ResidentAlias",
            "ElectricianAlias"
        ]
    }

For more information, see `Authorizing direct calls to AWS services using AWS IoT Core credential provider <https://docs.aws.amazon.com/iot/latest/developerguide/authorizing-direct-aws.html>`__ in the *AWS IoT Core Developer Guide*.
