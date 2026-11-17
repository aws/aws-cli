**To purchase a Reserved Instance offering**

The following ``purchase-reserved-instances-offering`` example purchases a Reserved Instances offering, specifying an offering ID and instance count. ::

    aws ec2 purchase-reserved-instances-offering \
        --reserved-instances-offering-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --instance-count 3


Output::

    {
        "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Buy Reserved Instances for Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html>`__ in the *Amazon EC2 User Guide*.
