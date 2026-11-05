**To describe a gateway capability**

The following ``describe-gateway-capability-configuration`` example describes an OPC-UA source capability. ::

    aws iotsitewise describe-gateway-capability-configuration \
        --gateway-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --capability-namespace "iotsitewise:opcuacollector:1"

Output::

    {
        "gatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "capabilityNamespace": "iotsitewise:opcuacollector:1",
        "capabilityConfiguration": "{\"sources\":[{\"name\":\"Wind Farm #1\",\"endpoint\":{\"certificateTrust\":{\"type\":\"TrustAny\"},\"endpointUri\":\"opc.tcp://203.0.113.0:49320\",\"securityPolicy\":\"BASIC256\",\"messageSecurityMode\":\"SIGN_AND_ENCRYPT\",\"identityProvider\":{\"type\":\"Username\",\"usernameSecretArn\":\"arn:aws:secretsmanager:us-west-2:123456789012:secret:greengrass-factory1-auth-3QNDmM\"},\"nodeFilterRules\":[]},\"measurementDataStreamPrefix\":\"\"}]}",
        "capabilitySyncStatus": "IN_SYNC"
    }

For more information, see `OPC UA data sources for AWS IoT SiteWise Edge gateways <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/configure-sources-opcua.html>`__ in the *AWS IoT SiteWise User Guide*.