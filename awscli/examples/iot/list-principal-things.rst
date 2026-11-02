**To list the things attached with a principal**

The following ``list-principal-things`` example lists the things attached to the principal specified by an ARN. ::

    aws iot list-principal-things \
        --principal arn:aws:iot:us-west-2:123456789012:cert/2e1eb273792174ec2b9bf4e9b37e6c6c692345499506002a35159767055278e8

Output::

    {
        "things": [
            "DeskLamp",
            "TableLamp"
        ]
    }

For more information, see `Attach a thing or policy to a client certificate <https://docs.aws.amazon.com/iot/latest/developerguide/attach-to-cert.html>`__ in the *AWS IoT Core Developer Guide*.
