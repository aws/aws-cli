**Example 1: To list the values for a parameter**

The following ``get-parameters`` example lists the values for the three specified parameters. ::

    aws ssm get-parameters \
        --names "MyStringParameter" "MyStringListParameter" "MyInvalidParameterName"

Output::

    {
        "Parameters": [
            {
                "Name": "MyStringListParameter",
                "Type": "StringList",
                "Value": "alpha,beta,gamma",
                "Version": 1,
                "LastModifiedDate": 1582154764.222,
                "ARN": "arn:aws:ssm:us-east-2:111222333444:parameter/MyStringListParameter"
            },
            {
                "Name": "MyStringParameter",
                "Type": "String",
                "Value": "Vici",
                "Version": 3,
                "LastModifiedDate": 1582156117.545,
                "ARN": "arn:aws:ssm:us-east-2:111222333444:parameter/MyStringParameter"
            }
        ],
        "InvalidParameters": [
            "MyInvalidParameterName"
        ]
    }

For more information, see `Working with Parameter Store <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-working-with.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To list names and values of multiple parameters using the ``--query`` option**

The following ``get-parameters`` example lists the names and values for the specified parameters. ::

    aws ssm get-parameters \
        --names MyStringParameter MyStringListParameter \
        --query "Parameters[*].{Name:Name,Value:Value}"

Output::
  
    [
        {
            "Name": "MyStringListParameter",
            "Value": "alpha,beta,gamma"
        },
        {
            "Name": "MyStringParameter",
            "Value": "Vidi"
        }
    ]

For more information, see `Working with Parameter Store <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-working-with.html>`__ in the *AWS Systems Manager User Guide*.
