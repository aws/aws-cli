**Example 1: To authorize access to an EC2 security group**

The following ``authorize-cluster-security-group-ingress`` example authorizes access to a named Amazon EC2 security group. ::

    aws redshift authorize-cluster-security-group-ingress \
        --cluster-security-group-name mysecuritygroup \
        --ec2-security-group-name myec2securitygroup \
        --ec2-security-group-owner-id 123445677890

**Example 2: To authorize access to a CIDR range**

The following ``authorize-cluster-security-group-ingress`` example authorizes access to a CIDR range. ::

    aws redshift authorize-cluster-security-group-ingress \
        --cluster-security-group-name mysecuritygroup \
        --cidrip 192.168.100.100/32


