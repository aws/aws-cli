**To create a policy that enables Proxy Protocol on your load balancer**

This example creates a policy that enables Proxy Protocol on your TCP load balancer.

Command::

     aws elb create-load-balancer-policy --load-balancer-name MyLoadBalancer --policy-name EnableProxyProtocol  --policy-type-name ProxyProtocolPolicyType --policy-attributes AttributeName=ProxyProtocol,AttributeValue=True


Output::

     {}

**To create an SSL negotiation policy using the recommended security policy**

This example creates an SSL negotiation policy for your HTTPS load balancer using the recommended security policy.

Command::

      aws elb create-load-balancer-policy --load-balancer-name MyHTTPSLoadBalancer  --policy-name MySSLNegotiationPolicy  --policy-type-name SSLNegotiationPolicyType --policy-attributes AttributeName=Reference-Security-Policy,AttributeValue=
      ELBSecurityPolicy-2014-01


Output::

     {}

**To create an SSL negotiation policy using a custom security policy**

This example creates an SSL negotiation policy for your HTTPS load balancer using a custom security policy by enabling the protocols and the ciphers.

Command::

       aws elb create-load-balancer-policy --load-balancer-name MyHTTPSLoadBalancer --policy-name MySSLNegotiationPolicy --policy-type-name SSLNegotiationPolicyType  --policy-attributes AttributeName=Protocol-SSLv3,AttributeValue=true
       AttributeName=Protocol-TLSv1.1,AttributeValue=true AttributeName=DHE-RSA-AES256-SHA256,AttributeValue=true AttributeName=Server-Defined-Cipher-Order,AttributeValue=true


Output::

       {}

**To create a back-end server authentication policy**

This example creates a back-end server authentication policy that enables authentication on your back-end instance.

Command::

        aws elb create-load-balancer-policy --load-balancer-name MyHTTPSLoadBalancer  --policy-name MyBackendServerAuthenticationPolicy  --policy-type-name BackendServerAuthenticationPolicyType --policy-attributes AttributeName=PublicKeyPolicy
        Name,AttributeValue=MyPublicKeyPolicy


Output::

        {}

