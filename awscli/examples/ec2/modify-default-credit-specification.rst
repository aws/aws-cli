**To modify the default credit option**

The following ``modify-default-credit-specification`` example modifies the default credit option for T2 instances. ::

    aws ec2 modify-default-credit-specification \
        --instance-family t2 \
        --cpu-credits unlimited

Output::

    {
        "InstanceFamilyCreditSpecification": {
            "InstanceFamily": "t2",
            "CpuCredits": "unlimited"
        }
    }

For more information, see `Configure burstable performance instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-how-to.html>`__ in the *Amazon EC2 User Guide*.
