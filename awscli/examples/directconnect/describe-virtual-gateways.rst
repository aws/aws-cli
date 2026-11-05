**To list virtual private gateways**

The following ``describe-virtual-gateways`` example lists virtual private gateways owned by your AWS account. ::

    aws directconnect describe-virtual-gateways

Output::

    {
        "virtualGateways": [
            {
                "virtualGatewayId": "vgw-aba37db6",
                "virtualGatewayState": "available"
            }
        ]
    }

For more information, see `Direct Connect virtual private gateway associations <https://docs.aws.amazon.com/directconnect/latest/UserGuide/virtualgateways.html>`__ in the *AWS Direct Connect User Guide*.
