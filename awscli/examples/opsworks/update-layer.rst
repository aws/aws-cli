**To update a layer**

The following example updates a specified layer to use Amazon EBS-optimized instances. ::

  aws opsworks --region us-east-1 update-layer --layer-id 888c5645-09a5-4d0e-95a8-812ef1db76a4 --use-ebs-optimized-instances

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Editing an OpsWorks Layer's Configuration`_ in the *AWS OpsWorks User Guide*.

.. _`Editing an OpsWorks Layer's Configuration`: http://docs.aws.amazon.com/opsworks/latest/userguide/workinglayers-basics-edit.html

