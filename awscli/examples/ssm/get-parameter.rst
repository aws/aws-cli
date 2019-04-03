**To list the value for a parameter**

This example lists the value for a parameter.

Command::

  aws ssm get-parameter --name "helloWorld"
  
Output::

  {
    "Parameter": {
        "Name": "helloWorld",
        "Type": "String",
        "Value": "Good day sunshine",
        "Version": 1,
        "LastModifiedDate": 1530018761.888,
        "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/helloWorld"
    }
  }

**To decrypt the value for a parmeter"

This example decrypts the value of a SecureString parameter.

Command::
  
  aws ssm get-parameter --name "helloSecureWorld" --with-decryption

Output::
  
  {
    "Parameter": {
        "Name": "helloSecureWorld",
        "Type": "SecureString",
        "Value": "Good day sunshine",
        "Version": 1,
        "LastModifiedDate": 1530018761.888,
        "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/helloSecureWorld"
    }
  }
