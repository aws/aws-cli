**Example 1: To remove an instance's affinity with a Dedicated Host**

The following ``modify-instance-placement`` example removes an instance's affinity with a Dedicated Host and enables it to launch on any available Dedicated Host in your account that supports its instance type. ::

    aws ec2 modify-instance-placement \
        --instance-id i-0e6ddf6187EXAMPLE \
        --affinity default

Output::

    {
        "Return": true
    }

**Example 2: To establish affinity between an instance and the specified Dedicated Host**

The following ``modify-instance-placement`` example establishes a launch relationship between an instance and a Dedicated Host. The instance is only able to run on the specified Dedicated Host. ::

    aws ec2 modify-instance-placement \
        --instance-id i-0e6ddf6187EXAMPLE \
        --affinity host \
        --host-id i-0e6ddf6187EXAMPLE

Output::

    {
        "Return": true
    }

For more information, see `Modifying Instance Tenancy and Affinity <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/how-dedicated-hosts-work.html#moving-instances-dedicated-hosts>`__ in the *Amazon Elastic Compute Cloud User Guide for Linux Instances*.
