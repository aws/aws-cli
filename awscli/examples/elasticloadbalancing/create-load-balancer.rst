**To create HTTP load balancer in EC2-Classic**

This example creates an HTTP load balancer in EC2-Classic.

Command::

  aws elb create-load-balancer  --load-balancer-name MyLoadBalancer --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80  --availability-zones us-east-1a us-east-1b

Output::

  {
    "DNSName": "MyLoadBalancer-012345678.us-east-1.elb.amazonaws.com"
  }

**To create HTTPS load balancer in EC2-Classic**

This example creates an HTTPS load balancer in EC2-Classic.

Command::

  aws elb create-load-balancer --load-balancer-name MyHTTPSLoadBalancer --listeners Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTPS,InstancePort=443,SSLCertificateId=arn:aws:iam::012345678901:server-certificate/scert  --availability-zones us-east-1a us-east-1b

Output::

  {
    "DNSName": "MyHTTPSLoadBalancer-012345678.us-east-1.elb.amazonaws.com"
  }

**To create HTTP load balancer in Amazon VPC**

This example creates an HTTP load balancer in Amazon Virtual Private Cloud (Amazon VPC).

Command::

  aws elb create-load-balancer --load-balancer-name MyVPCLoadBalancer --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 --subnets subnet-15aaab61 --security-groups sg-a61988c3

Output::

  {
    "DNSName": "MyVPCLoadBalancer-012345678.us-east-1.elb.amazonaws.com"
  }

**To create an Internal load balancer in Amazon VPC**

This example creates an Internal HTTP load balancer in Amazon VPC.

Command::

  aws elb create-load-balancer --load-balancer-name MyInternalLoadBalancer --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 --subnets subnet-a85db0df --scheme internal --security-groups sg-a61988c3

Output::

  {
    "DNSName": "internal-MyInternalLoadBalancer-012345678.us-east-1.elb.amazonaws.com"
  }

