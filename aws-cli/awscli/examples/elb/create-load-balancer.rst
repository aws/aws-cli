**Example 1: To create an HTTP load balancer**

The following ``create-load-balancer`` example creates a load balancer with an HTTP listener in a VPC. ::

    aws elb create-load-balancer \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" \
        --subnets subnet-15aaab61 \
        --security-groups sg-a61988c3

Output::

    {
        "DNSName": "my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"
    }


The following ``create-load-balancer`` example creates a load balancer with an HTTP listener in EC2-Classic. ::

    aws elb create-load-balancer \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" \
        --availability-zones us-west-2a us-west-2b

Output::

    {
        "DNSName": "my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
    }

For more information, see `Create an internet-facing Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-getting-started.html>`__ in the *Classic Load Balancers User Guide*.

**Example 2: To create an HTTPS load balancer**

The following ``create-load-balancer`` example creates a load balancer with an HTTPS listener in a VPC. ::

    aws elb create-load-balancer \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" "Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTP,InstancePort=80,SSLCertificateId=arn:aws:iam::123456789012:server-certificate/my-server-cert" \
        --subnets subnet-15aaab61 \
        --security-groups sg-a61988c3

Output::

    {
        "DNSName": "my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"
    }

The following ``create-load-balancer`` example creates a load balancer with an HTTPS listener in EC2-Classic. ::

    aws elb create-load-balancer \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" "Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTP,InstancePort=80,SSLCertificateId=arn:aws:iam::123456789012:server-certificate/my-server-cert" \
        --availability-zones us-west-2a us-west-2b

Output::

    {
        "DNSName": "my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
    }

For more information, see `Create a Classic Load Balancer with an HTTPS listener <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-create-https-ssl-load-balancer.html>`__ in the *Classic Load Balancers User Guide*.

**Example 3: To create an internal load balancer**

The following ``create-load-balancer`` example creates an internal load balancer with an HTTP listener in a VPC. ::

    aws elb create-load-balancer \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80" \
        --scheme internal \
        --subnets subnet-a85db0df \
        --security-groups sg-a61988c3

Output::

    {
        "DNSName": "internal-my-load-balancer-123456789.us-west-2.elb.amazonaws.com"
    }

For more information, see `Create an internal Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-create-internal-load-balancer.html>`__ in the *Classic Load Balancers User Guide*.
