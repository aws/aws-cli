**Example 1: To modify the attachment attribute of a network interface**

The following ``modify-network-interface-attribute`` example modifies the ``attachment`` attribute of the specified network interface. ::

    aws ec2 modify-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --attachment AttachmentId=eni-attach-43348162,DeleteOnTermination=false

This command produces no output.

**Example 2: To modify the description attribute of a network interface**

The following ``modify-network-interface-attribute`` example modifies the ``description`` attribute of the specified network interface. ::

    aws ec2 modify-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --description "My description"

This command produces no output.

**Example 3: To modify the groupSet attribute of a network interface**

The following ``modify-network-interface-attribute`` example modifies the ``groupSet`` attribute of the specified network interface. ::

    aws ec2 modify-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --groups sg-903004f8 sg-1a2b3c4d

This command produces no output.

**Example 4: To modify the sourceDestCheck attribute of a network interface**

The following ``modify-network-interface-attribute`` example modifies the ``sourceDestCheck`` attribute of the specified network interface. ::

    aws ec2 modify-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --no-source-dest-check

This command produces no output.

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.
