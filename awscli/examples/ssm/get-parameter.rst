**Example 1: To display the value of a parameter**

The following ``get-parameter`` example lists the value for the specified single parameter. ::

    aws ssm get-parameter \
        --name "MyStringParameter"

Output::

    {
        "Parameter": {
            "Name": "MyStringParameter",
            "Type": "String",
            "Value": "Veni",
            "Version": 1,
            "LastModifiedDate": 1530018761.888,
            "ARN": "arn:aws:ssm:us-east-2:111222333444:parameter/MyStringParameter"
        }
    }

**Example 2: To decrypt the value of a SecureString parameter**

The following ``get-parameter`` example decrypts the value of the specified ``SecureString`` parameter. ::

    aws ssm get-parameter \
        --name "MySecureStringParameter" \
        --with-decryption

Output::

    {
        "Parameter": {
            "Name": "MySecureStringParameter",
            "Type": "SecureString",
            "Value": "16679b88-310b-4895-a943-e0764EXAMPLE",
            "Version": 2,
            "LastModifiedDate": 1582155479.205,
            "ARN": "arn:aws:ssm:us-east-2:111222333444:parameter/MySecureStringParameter"
        }
    }

For more information, see `Working with Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-working.html>`_ in the *AWS Systems Manager User Guide*.
