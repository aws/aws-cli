**Example 1: To remove the rule that allows outbound traffic to a specific address range**

The following ``revoke-security-group-egress`` example command removes the rule that grants access to the specified address ranges on TCP port 80. ::

    aws ec2 revoke-security-group-egress \
        --group-id sg-026c12253ce15eff7 \
        --ip-permissions '[{"IpProtocol":"tcp","FromPort":80,"ToPort":80,"IpRanges":[{"CidrIp":"10.0.0.0/16"}]}]'

If it succeeds, this command produces no output if ``output`` is set to ``text``, or ``{"Return": true}`` if ``output`` is set to ``json``.
If no matching rule is found, this command returns an error.

For more information, see `Security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To remove the rule that allows outbound traffic to a specific security group**

The following ``revoke-security-group-egress`` example command removes the rule that grants access to the specified security group on TCP port 80. ::

    aws ec2 revoke-security-group-egress \
        --group-id sg-026c12253ce15eff7 \
        --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,"UserIdGroupPairs": [{"GroupId": "sg-06df23a01ff2df86d"}]}]'

If it succeeds, this command produces no output if ``output`` is set to ``text``, or ``{"Return": true}`` if ``output`` is set to ``json``.
If no matching rule is found, this command returns an error.

For more information, see `Security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.