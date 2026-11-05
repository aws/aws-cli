**To register a thing**

The following ``register-thing`` example registers a thing using a provisioning template. ::

    aws iot register-thing \
        --template-body '{"Parameters":{"ThingName":{"Type":"String"},"AWS::IoT::Certificate::Id":{"Type":"String"}},"Resources": {"certificate":{"Properties":{"CertificateId":{"Ref":"AWS::IoT::Certificate::Id"},"Status":"Active"},"Type":"AWS::IoT::Certificate"},"policy":{"Properties":{"PolicyName":"MyIotPolicy"},"Type":"AWS::IoT::Policy"},"thing":{"OverrideSettings":{"AttributePayload":"MERGE","ThingGroups":"DO_NOTHING","ThingTypeName":"REPLACE"},"Properties":{"AttributePayload":{},"ThingGroups":[],"ThingName":{"Ref":"ThingName"},"ThingTypeName":"VirtualThings"},"Type":"AWS::IoT::Thing"}}}' \
        --parameters '{"ThingName":"Register-thing-trial-1","AWS::IoT::Certificate::Id":"799a9ea048a1e6aea42b55EXAMPLEf8697b4bafcd77a318a3068e30404b9233c"}'

Output::

    {
        "certificatePem": "-----BEGIN CERTIFICATE-----\nMIIDWTCCAkGgAwIBAgIUYLk81I35cIppobpwHiOJ2jNjboIwDQYJKoZIhvcNAQEL\nBQAwTTFLMEkGA1UECwxCQW1hem9uIFdlYiBTZXJ2aWNlcyBPPUFtYXpvbi5jb20g\nSW5jLiBMPVNlYXR0bGUgU1Q9V2FzaGluZ3RvbiBDPVVTMB4XDTIwMDcyMzE2NDUw\nOVoXDTQ5MTIzMTIzNTk1OVowHjEcMBoGA1UEAwwTQVdTIElvVCBDZXJ0aWZpY2F0\nZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAO71uADhdBajqTmgrMV5\nmCFfBZQRMo1MdtVoZr2X+M4MzL+RARrtUzH9a2SMAckeX8KeblIOTKzORIRDXnyE\n6lVOwjgAsd0ku22rFxex4eG2ikha7pYYkvuToqA7L3TxItRvfKrxRI4ZfJoFPip4\nKqiuBJVNOGKTcQHd1RNOrddwwu6kFJLeKDmEXAMPLEdUF0N+qfR9yKnZQkm+g6Q2\nGXu7u0W3hn6nlRN8qVoka0uW12p53xM7oHVzGf+cxKBxlbOhGkp6yCfTSkUBm3Sp\n9zLw35kiHXVm4EVpwgNlnk6XcIGIkw8a/iy4pzmvuGAANY1/uU/zgCjymwZT5S30\nBV0CAwEAAaNgMF4wHwYDVR0jBBgwFoAUGx0tCcU3q2n1WXAuUCv6hugXjKswHQYD\nVR0OBBYEFOVtvZ9Aj2RYFnkX7Iu01XTRUdxgMAwGA1UdEwEB/wQCMAAwDgYDVR0P\nAQH/BAQDAgeAMA0GCSqGSIb3DQEBCwUAA4IBAQCXCQcpOtubS5ftOsDMTcpP/jNX\nDHyArxmjpSc2aCdmm7WX59lTKWyAdxGAvqaDVWqTo0oXI7tZ8w7aINlGi5pXnifx\n3SBebMUoBbTktrC97yUaeL025mCFv8emDnTR/fE7PTsBKjW0g/rrfpwBxZLXDFwN\nnqkQjy3EDfifj26j0xYIqqWMPogyn4srOCKynS5wMJuQZlHQOnabVwnwK4Y0Mflp\np9+4susFUR9aT3BT1AcIwqSpzhlKhh4Iz7NDkRn4amsUT210jg/zOO1Ow+BTHcVQ\nJly8XDu0CWSu04q6SnaBzHmlySIajxuRTP/AdfRouP1OXe+qlbPOBcvVvF8o\n-----END CERTIFICATE-----\n",
        "resourceArns": {
            "certificate": "arn:aws:iot:us-west-2:123456789012:cert/799a9ea048a1e6aea42b55EXAMPLEf8697b4bafcd77a318a3068e30404b9233c",
            "thing": "arn:aws:iot:us-west-2:123456789012:thing/Register-thing-trial-1"
        }
    }

For more information, see `Provisioning by trusted user <https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html#trusted-user>`__ in the *AWS IoT Core Developers Guide*.
