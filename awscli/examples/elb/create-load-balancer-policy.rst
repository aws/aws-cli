**Example 1: To create a policy that enables Proxy Protocol on a load balancer**

The following ``create-load-balancer-policy`` example creates a policy that enables Proxy Protocol on the specified load balancer. ::

    aws elb create-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-ProxyProtocol-policy \
        --policy-type-name ProxyProtocolPolicyType \
        --policy-attributes AttributeName=ProxyProtocol,AttributeValue=true

This command produces no output.

For more information, see `Configure proxy protocol for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-proxy-protocol.html>`__ in the *Classic Load Balancers User Guide*.

**Example 2: To create an SSL negotiation policy using the recommended security policy**

The following ``create-load-balancer-policy`` example creates an SSL negotiation policy for the specified HTTPS load balancer using the recommended security policy. ::

    aws elb create-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-SSLNegotiation-policy \
        --policy-type-name SSLNegotiationPolicyType \
        --policy-attributes AttributeName=Reference-Security-Policy,AttributeValue=ELBSecurityPolicy-2015-03

This command produces no output.

For more information, see `SSL negotiation configurations for Classic Load Balancers <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-ssl-security-policy.html>`__ in the *Classic Load Balancers User Guide*.

**Example 3: To create an SSL negotiation policy using a custom security policy**

The following ``create-load-balancer-policy`` example creates an SSL negotiation policy for your HTTPS load balancer using a custom security policy by enabling the protocols and the ciphers. ::

    aws elb create-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-SSLNegotiation-policy \
        --policy-type-name SSLNegotiationPolicyType \
        --policy-attributes AttributeName=Protocol-SSLv3,AttributeValue=true AttributeName=Protocol-TLSv1.1,AttributeValue=true AttributeName=DHE-RSA-AES256-SHA256,AttributeValue=true AttributeName=Server-Defined-Cipher-Order,AttributeValue=true

This command produces no output.

For more information, see `Update the SSL negotiation configuration of your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/ssl-config-update.html>`__ in the *Classic Load Balancers User Guide*.

**Example 4: To create a public key policy**

The following ``create-load-balancer-policy`` example creates a public key policy. ::

    aws elb create-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-PublicKey-policy \
        --policy-type-name PublicKeyPolicyType \
        --policy-attributes AttributeName=PublicKey,AttributeValue=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwAYUjnfyEyXr1pxjhFWBpMlggUcqoi3kl+dS74kj//c6x7ROtusUaeQCTgIUkayttRDWchuqo1pHC1u+n5xxXnBBe2ejbb2WRsKIQ5rXEeixsjFpFsojpSQKkzhVGI6mJVZBJDVKSHmswnwLBdofLhzvllpovBPTHe+o4haAWvDBALJU0pkSI1FecPHcs2hwxf14zHoXy1e2k36A64nXW43wtfx5qcVSIxtCEOjnYRg7RPvybaGfQ+v6Iaxb/+7J5kEvZhTFQId+bSiJImF1FSUT1W1xwzBZPUbcUkkXDj45vC2s3Z8E+Lk7a3uZhvsQHLZnrfuWjBWGWvZ/MhZYgEXAMPLE

This command produces no output.

For more information, see `Create a Classic Load Balancer with an HTTPS listener <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-create-https-ssl-load-balancer.html>`__ in the *Classic Load Balancers User Guide*.

**Example 5: To create a backend server authentication policy**

The following ``create-load-balancer-policy`` example creates a backend server authentication policy that enables authentication on your backend instance using a public key policy. ::

    aws elb create-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-authentication-policy \
        --policy-type-name BackendServerAuthenticationPolicyType \
        --policy-attributes AttributeName=PublicKeyPolicyName,AttributeValue=my-PublicKey-policy

This command produces no output.

For more information, see `Create a Classic Load Balancer with an HTTPS listener <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-create-https-ssl-load-balancer.html>`__ in the *Classic Load Balancers User Guide*.
