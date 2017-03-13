**To get a value history for a parameter**

This example lists the value history for a parameter.

Command::

  aws ssm get-parameter-history --name "welcome"
  
Output::

  {
    "Parameters": [
        {
            "LastModifiedUser": "arn:aws:iam::812345678901:user/admin",
            "LastModifiedDate": 1487880053.085,
            "Type": "String",
            "Name": "welcome",
            "Value": "helloWorld"
        }
    ]
  }
