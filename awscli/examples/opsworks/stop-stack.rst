**To stop a stack's instances**

The following example stops all of a stack's 24/7 instances.
To stop a particular instance, use ``stop-instance``. ::

  aws opsworks --region us-east-1 stop-stack --stack-id 8c428b08-a1a1-46ce-a5f8-feddc43771b8

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: No output.

**More Information**

For more information, see `Stopping an Instance`_ in the *AWS OpsWorks User Guide*.

.. _`Stopping an Instance`: http://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances-starting.html#workinginstances-starting-stop

