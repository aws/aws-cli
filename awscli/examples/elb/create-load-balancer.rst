**To create an HTTP load balancer**

This example creates an HTTP load balancer in a VPC.

Command::

  aws elb create-load-balancer --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" --subnets subnet-15aaab61 --security-groups sg-a61988c3

Output::

  {
      "DNSName": "my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"
  }


This example creates an HTTP load balancer in EC2-Classic.

Command::

  aws elb create-load-balancer --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" --availability-zones us-west-2a us-west-2b

Output::

  {
      "DNSName": "my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
  }

**To create an HTTPS load balancer**

This example creates an HTTPS load balancer in a VPC.

Command::

  aws elb create-load-balancer --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" "Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTPS,InstancePort=443,SSLCertificateId=arn:aws:iam::123456789012:server-certificate/my-server-cert" --subnets subnet-15aaab61 --security-groups sg-a61988c3

Output::

  {
      "DNSName": "my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"
  }

This example creates an HTTPS load balancer in EC2-Classic.

Command::

  aws elb create-load-balancer --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" "Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTPS,InstancePort=443,SSLCertificateId=arn:aws:iam::123456789012:server-certificate/my-server-cert" --availability-zones us-west-2a us-west-2b

Output::

  {
      "DNSName": "my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
  }

**To create an internal load balancer**

This example creates an internal HTTP load balancer in a VPC.

Command::

  aws elb create-load-balancer --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" --scheme internal --subnets subnet-a85db0df --security-groups sg-a61988c3

Output::

  {
      "DNSName": "internal-my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
  }

