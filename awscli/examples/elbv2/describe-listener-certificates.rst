**To describe the certificates for a secure listener**

The following ``describe-listener-certificates`` example describes the certificates for the specified secure listener. ::

    aws elbv2 describe-listener-certificates \
        --listener-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2

Output::

    {
        "Certificates": [
            {
                "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "IsDefault": false
            },
            {
                "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "IsDefault": false
            },
            {
                "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "IsDefault": true
            }
        ]
    }

For more information, see `SSL certificates for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/https-listener-certificates.html>`__ in the *Application Load Balancers Guide*.
