**To remove a certificate from a secure listener**

The following ``remove-listener-certificates`` example removes the specified certificate from the specified secure listener. ::

    aws elbv2 remove-listener-certificates \
        --listener-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2 \
        --certificates CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `SSL certificates for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/https-listener-certificates.html>`__ in the *Application Load Balancers Guide*.
