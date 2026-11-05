**To send a an SSH public key to an instance**

The following ``send-ssh-public-key`` example sends the specified SSH public key to the specified instance. The key is used to authenticate the specified user. ::

    aws ec2-instance-connect send-ssh-public-key \
        --instance-id i-1234567890abcdef0 \
        --instance-os-user ec2-user \
        --availability-zone us-west-2b \
        --ssh-public-key file://path/my-rsa-key.pub

Contents of ``my-rsa-key.pub``::

    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCEXAMPLEKEY ec2-user@example

This command produces no output.

For more information, see `Connect to a Linux instance using EC2 Instance Connect <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html>`__ in the *Amazon EC2 User Guide*.
