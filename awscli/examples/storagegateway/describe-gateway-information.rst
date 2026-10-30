**To describe a gateway**

The following ``describe-gateway-information`` example returns metadata about the specified gateway.
To specify which gateway to describe, use the Amazon Resource Name (ARN) of the gateway in the command.

This example specifies a gateway with the id ``sgw-12A3456B`` in account ``123456789012``. ::

    aws storagegateway describe-gateway-information \
        --gateway-arn "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B"

This command outputs a JSON block that contains metadata about about the gateway such as its name,
network interfaces, configured time zone, and the state (whether the gateway is running or not).

Output::

    {
        "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B",
        "GatewayId": "sgw-12A3456B",
        "GatewayName": "my-gateway",
        "GatewayTimezone": "GMT-8:00",
        "GatewayState": "RUNNING",
        "GatewayNetworkInterfaces": [
            {
                "Ipv4Address": "10.0.0.25"
            }
        ],
        "GatewayType": "STORED",
        "Tags": [],
        "HostEnvironment": "VMWARE",
        "EndpointType": "STANDARD"
    }

For more information, see `Managing Your Volume Gateway <https://docs.aws.amazon.com/storagegateway/latest/vgw/managing-gateway-common.html>`__ in the *AWS Storage Gateway Volume Gateway User Guide*.
