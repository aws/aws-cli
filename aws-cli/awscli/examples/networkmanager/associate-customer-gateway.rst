**To associate a customer gateway**

The following ``associate-customer-gateway`` example associates customer gateway ``cgw-11223344556677889`` in the specified global network with device ``device-07f6fd08867abc123``. ::

    aws networkmanager associate-customer-gateway \
        --customer-gateway-arn arn:aws:ec2:us-west-2:123456789012:customer-gateway/cgw-11223344556677889 \
        --global-network-id global-network-01231231231231231 \
        --device-id device-07f6fd08867abc123

Output::

    {
        "CustomerGatewayAssociation": {
            "CustomerGatewayArn": "arn:aws:ec2:us-west-2:123456789012:customer-gateway/cgw-11223344556677889",
            "GlobalNetworkId": "global-network-01231231231231231",
            "DeviceId": "device-07f6fd08867abc123",
            "State": "PENDING"
        }
    }

For more information, see `Gateway associations in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/gw-association.html>`__ in the *Transit Gateway Network Manager Guide*.
