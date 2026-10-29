**To delete a NAT gateway**

The following ``delete-nat-gateway`` example deletes NAT gateway ``nat-04ae55e711cec5680``. ::

    aws ec2 delete-nat-gateway \
        --nat-gateway-id nat-04ae55e711cec5680

Output::

    {
        "NatGatewayId": "nat-04ae55e711cec5680"
    }

For more information, see `Work with NAT gateways <https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-working-with.html>`__ in the *Amazon VPC User Guide*.
