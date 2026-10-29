**To replace a network ACL entry**

The following ``replace-network-acl-entry`` example replaces an entry for the specified network ACL. The new rule 100 allows ingress traffic from 203.0.113.12/24 on UDP port 53 (DNS) into any associated subnet. ::

    aws ec2 replace-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 100 \
        --protocol udp \
        --port-range From=53,To=53 \
        --cidr-block 203.0.113.12/24 \
        --rule-action allow

This command produces no output.

For more information, see `Network ACL rules <https://docs.aws.amazon.com/vpc/latest/userguide/nacl-rules.html>`__ in the *Amazon VPC User Guide*.
