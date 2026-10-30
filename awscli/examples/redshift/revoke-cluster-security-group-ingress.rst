**Example 1: To revoke access from an EC2 security group**

The following ``revoke-cluster-security-group-ingress`` example revokes access to a named Amazon EC2 security group. ::

    aws redshift revoke-cluster-security-group-ingress --cluster-security-group-name mysecuritygroup --ec2-security-group-name myec2securitygroup --ec2-security-group-owner-id 123445677890


**Example 2: To revoke access to a CIDR range**

The following ``revoke-cluster-security-group-ingress`` example revokes access to a CIDR range. ::

    aws redshift revoke-cluster-security-group-ingress --cluster-security-group-name mysecuritygroup --cidrip 192.168.100.100/32


