**To list parameters in a specific path**

This example lists parameters within a specific hierarchy.

Command::

  aws ssm get-parameters-by-path --path "/site/newyork/department/"
  
Output::

  {
    "Parameters": [
        {
            "Name": "/site/newyork/department/marketing",
            "Type": "String",
            "Value": "Floor 2",
            "Version": 1,
            "LastModifiedDate": 1530018761.888,
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/site/newyork/department/marketing"
        },
        {
            "Name": "/site/newyork/department/infotech",
            "Type": "String",
            "Value": "Floor 3",
            "Version": 1,
            "LastModifiedDate": 1530018823.429,
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter//site/newyork/department/infotech"
        },
        ...
    ]
  }
