**To reset a network interface attribute**

The following ``reset-network-interface-attribute`` example resets the value of the source/destination checking attribute to ``true``. ::

    aws ec2 reset-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --source-dest-check sourceDestCheck

This command produces no output.

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.
