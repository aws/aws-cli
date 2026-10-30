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
                "ARN": "arn:aws:ssm:us-west-2:123456789012:parameter/MyStringListParameter",
                "DataType": "text"
            },
            {
                "Name": "MyStringParameter",
                "Type": "String",
                "Value": "Vici",
                "Version": 3,
                "LastModifiedDate": 1582156117.545,
                "ARN": "arn:aws:ssm:us-west-2:123456789012:parameter/MyStringParameter",
                "DataType": "text"
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

**Example 3: To display the value of a parameter using labels**

The following ``get-parameters`` example lists the values for the specified parameters, one specified by label and one specified by version. ::

    aws ssm get-parameters \
        --names "MyLabelParameter:label" "MyVersionParameter:2"

Output::

    {
        "Parameters": [
            {
                "Name": "MyLabelParameter",
                "Type": "String",
                "Value": "parameter by label",
                "Version": 1,
                "Selector": ":label",
                "LastModifiedDate": "2021-07-12T09:49:15.865000-07:00",
                "ARN": "arn:aws:ssm:us-west-2:123456789111:parameter/MyLabelParameter",
                "DataType": "text"
            },
            {
                "Name": "MyVersionParameter",
                "Type": "String",
                "Value": "parameter by version",
                "Version": 2,
                "Selector": ":2",
                "LastModifiedDate": "2021-03-24T16:20:28.236000-07:00",
                "ARN": "arn:aws:ssm:us-west-2:123456789111:parameter/MyVersionParameter",
                "DataType": "text"
            }
        ],
        "InvalidParameters": []
    }

For more information, see `Working with parameter labels <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-labels.html>`__ in the *AWS Systems Manager User Guide*.