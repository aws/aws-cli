**To list all Parameters**

This example lists all parameters.

Command::

  aws ssm describe-parameters
  
Output::

  {
    "Parameters": [
        {
            "LastModifiedUser": "arn:aws:iam::809632081692:user/admin",
            "LastModifiedDate": 1487880325.324,
            "Type": "String",
            "Name": "welcome"
        }
    ]
  }

**To list all Parameters matching specific metadata**

This example lists all parameters matching ``Name`` value ``helloWorld``.

Command::

  aws ssm describe-parameters --filters "Key=Name,Values=helloWorld"
