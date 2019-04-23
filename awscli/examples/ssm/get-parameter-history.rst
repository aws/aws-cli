**To get a value history for a parameter**

This example lists the value history for a parameter.

Command::

  aws ssm get-parameter-history --name "welcome"
  
Output::

  {
    "Parameters": [
        {
            "Name": "welcome",
            "Type": "String",
            "LastModifiedDate": 1542308384.49,
            "LastModifiedUser": "arn:aws:sts::123456789012:assumed-role/Administrator",
            "Value": "1",
            "Version": 1,
            "Labels": []
        }
    ]
  }
