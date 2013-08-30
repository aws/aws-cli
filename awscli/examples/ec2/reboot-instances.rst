**To reboot an Amazon EC2 instance**

This example reboots a instance with the instance ID ``i-1a2b3c4d``.

Command::

  aws ec2 reboot-instances --instance-ids i-1a2b3c4d

Output::

    {
        "return": "true"
    }

For more information, see `Reboot Your Instance`_ in the *Amazon Elastic Compute Cloud User Guide*.

.. _`Reboot Your Instance`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-reboot.html

