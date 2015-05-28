**To modify the attachment attribute of a network interface**

This example command modifies the <code>attachment</code> attribute of the specified network interface.

Command::

  aws ec2 modify-network-interface-attribute --network-interface-id eni-686ea200 --attachment AttachmentId=eni-attach-43348162,DeleteOnTermination=false


**To modify the description attribute of a network interface**

This example command modifies the <code>description</code> attribute of the specified network interface.

Command::

  aws ec2 modify-network-interface-attribute --network-interface-id eni-686ea200 --description "My description"
  

**To modify the groupSet attribute of a network interface**

This example command modifies the <code>groupSet</code> attribute of the specified network interface.

Command::

  aws ec2 modify-network-interface-attribute --network-interface-id eni-686ea200 --groups sg-903004f8 sg-1a2b3c4d
  

**To modify the sourceDestCheck attribute of a network interface**

This example command modifies the <code>sourceDestCheck</code> attribute of the specified network interface.

Command::

  aws ec2 modify-network-interface-attribute --network-interface-id eni-686ea200 --no-source-dest-check
