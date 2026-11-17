**To create a network ACL entry**

The following ``create-network-acl-entry`` example creates an entry for the specified network ACL. The rule allows ingress traffic from any IPv4 address (0.0.0.0/0) on UDP port 53 (DNS) into any associated subnet. ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 100 \
        --protocol udp \
        --port-range From=53,To=53 \
        --cidr-block 0.0.0.0/0 \
        --rule-action allow

This command produces no output.

For more information, see `Network ACL rules <https://docs.aws.amazon.com/vpc/latest/userguide/nacl-rules.html>`__ in the *Amazon VPC User Guide*.

The following ``create-network-acl-entry`` example creates a rule for the specified network ACL that allows ingress traffic from any IPv6 address (::/0) on TCP port 80 (HTTP). ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 120 \
        --protocol tcp \
        --port-range From=80,To=80 \
        --ipv6-cidr-block ::/0 \
        --rule-action allow

This command produces no output.

For more information, see `Network ACL rules <https://docs.aws.amazon.com/vpc/latest/userguide/nacl-rules.html>`__ in the *Amazon VPC User Guide*.
