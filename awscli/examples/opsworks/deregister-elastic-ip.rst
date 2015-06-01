**To deregister an Elastic IP address from a stack**

The following example deregisters an Elastic IP address, identified by its IP address, from its stack. ::

  aws opsworks deregister-elastic-ip --region us-east-1 --elastic-ip 54.148.130.96 

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Deregistering Elastic IP Addresses`_ in the *AWS OpsWorks User Guide*.

.. _`Deregistering Elastic IP Addresses`: http://docs.aws.amazon.com/opsworks/latest/userguide/resources-dereg.html#resources-dereg-eip
