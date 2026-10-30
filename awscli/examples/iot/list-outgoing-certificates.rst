**To list certificates being transferred to a different AWS account**

The following ``list-outgoing-certificates`` example lists all device certificates that are in the process of being transferred to a different AWS account using the ``transfer-certificate`` command. ::

    aws iot list-outgoing-certificates

Output::

    {
        "outgoingCertificates": [
            {
                "certificateArn": "arn:aws:iot:us-west-2:123456789111:cert/488b6a7f2acdeb00a77384e63c4e40b18b1b3caaae57b7272ba44c45e3448142",
                "certificateId": "488b6a7f2acdeb00a77384e63c4e40b18b1b3caaae57b7272ba44c45e3448142",
                "transferredTo": "123456789111",
                "transferDate": 1569427780.441,
                "creationDate": 1569363250.557
            }
        ]
    }

For more information, see `Transfer a certificate to another account <https://docs.aws.amazon.com/iot/latest/developerguide/transfer-cert.html>`__ in the *AWS IoT Core Developer Guide*.
