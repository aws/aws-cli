**To release a Dedicated host from your account**

The following ``release-hosts`` example releases a Dedicated host from your account. Instances that are on the host must be stopped or terminated before the host can be released. ::

    aws ec2 release-hosts \
        --host-id=h-0029d6e3cacf1b3da

Output::

    {
        "Successful":  [
            "h-0029d6e3cacf1b3da"
        ],
        "Unsuccessful": []
    }

For more information, see `Release an Amazon EC2 Dedicated Host <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-releasing.html>`__ in the *Amazon EC2 User Guide*.
