**To detach a network interface from your instance**

The following ``detach-network-interface`` example detaches the specified network interface from the specified instance. ::

    aws ec2 detach-network-interface \
        --attachment-id eni-attach-66c4350a

This command produces no output.

For more information, see `Elastic network interfaces <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html>`__ in the *Amazon EC2 User Guide*.
