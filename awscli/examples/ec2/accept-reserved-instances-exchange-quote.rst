**To perform a Convertible Reserved Instance exchange**

The following ``accept-reserved-instances-exchange-quote`` example performs an exchange of the specified Convertible Reserved Instances. ::

    aws ec2 accept-reserved-instances-exchange-quote \
        --reserved-instance-ids a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --target-configurations OfferingId=a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "ExchangeId": "riex-e68ed3c1-8bc8-4c17-af77-811afexample"
    }

For more information, see `Exchange Convertible Reserved Instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-convertible-exchange.html>`__ in the *Amazon EC2 User Guide*.
