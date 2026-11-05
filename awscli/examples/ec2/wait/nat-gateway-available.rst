**To wait until a NAT gateway is available**

The following ``wait nat-gateway-available`` example pauses and resumes running only after it confirms that the specified NAT gateway is available. ::

    aws ec2 wait nat-gateway-available \
        --nat-gateway-ids nat-1234567890abcdef0

This command produces no output.

For more information, see `NAT gateways <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html>`__ in the *Amazon VPC User Guide*.
