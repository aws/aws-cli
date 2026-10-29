**To describe the default credit option**

The following ``get-default-credit-specification`` example describes the default credit option for T2 instances. ::

    aws ec2 get-default-credit-specification \
        --instance-family t2

Output::

    {
        "InstanceFamilyCreditSpecification": {
            "InstanceFamily": "t2",
            "CpuCredits": "standard"
        }
    }

For more information, see `Configure burstable performance instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-how-to.html#burstable-performance-instance-set-default-credit-specification-for-account>`__ in the *Amazon EC2 User Guide*.
