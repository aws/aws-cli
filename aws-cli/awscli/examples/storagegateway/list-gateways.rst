**To list gateways for an account**

The following ``list-gateways`` example lists all the gateways defined for an account. ::

    aws storagegateway list-gateways

This command outputs a JSON block that contains a list of gateway Amazon Resource Names (ARNs).

Output::

    {
        "Gateways": [
            {
                "GatewayId": "sgw-12A3456B",
                "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B",
                "GatewayType": "STORED",
                "GatewayOperationalState": "ACTIVE",
                "GatewayName": "my-gateway",
                "HostEnvironment": "VMWARE"
            },
            {
                "GatewayId": "sgw-23B4567C",
                "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-23B4567C",
                "GatewayType": "CACHED",
                "GatewayOperationalState": "ACTIVE",
                "GatewayName": "my-cached-gateway",
                "HostEnvironment": "VMWARE"
            }
        ]
    }

For more information, see `Understanding Storage Gateway Resources and Resource IDs <https://docs.aws.amazon.com/storagegateway/latest/vgw/storage-gateway-resource-id.html>`__ in the *AWS Storage Gateway Volume Gateway User Guide*.
