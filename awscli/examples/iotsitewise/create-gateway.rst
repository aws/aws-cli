**To create a gateway**

The following ``create-gateway`` example creates a gateway that runs on AWS IoT Greengrass. ::

    aws iotsitewise create-gateway \
        --gateway-name ExampleCorpGateway \
        --gateway-platform greengrass={groupArn=arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111}

Output::

    {
        "gatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "gatewayArn": "arn:aws:iotsitewise:us-west-2:123456789012:gateway/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Configuring a gateway <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/configure-gateway.html>`__ in the *AWS IoT SiteWise User Guide*.