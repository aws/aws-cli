**To list the values for a parameter**

This example lists the values for a parameter.

Command::

  aws ssm get-parameters --names "helloWorld"
  
Output::

  {
    "Parameters": [
        {
            "Name": "helloWorld",
            "Type": "String",
            "Value": "good day sunshine",
            "Version": 1,
            "LastModifiedDate": 1542308384.49,
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/helloWorld"
        }
    ],
    "InvalidParameters": []
  }

To list the name and value of multiple parameters the --query argument can be used with a list of names.

Command::
  
  aws ssm get-parameters --names key1 key2 --query "Parameters[*].{Name:Name,Value:Value}"

Output::
  
  [
    {
        "Name": "key1",
        "Value": "value1"
    },
    {
        "Name": "key2",
        "Value": "value2"
    }
  ]

