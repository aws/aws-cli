**To delete an instance**

The following example deletes a specified instance, which is identified by its instance ID.
It also deletes any attached Amazon Elastic Block Store (Amazon EBS) volumes or Elastic IP addresses.
You can obtain an instance ID by going to the instance's details page on the AWS OpsWorks console or by
running the ``describe-instances`` command.

If the instance is online, you must first stop the instance by calling ``stop-instance``, and then
wait until the instance has stopped. You can use ``describe-instances`` to check the instance status. ::

  aws opsworks delete-instance --region us-east-1 --instance-id 3a21cfac-4a1f-4ce2-a921-b2cfba6f7771

To retain the instance's Amazon EBS volumes or Elastic IP addresses,
use the ``--no-delete-volumes`` or ``--no-delete-elastic-ip`` arguments, respectively.

*Output*: None.

**More Information**

For more information, see `Deleting AWS OpsWorks Instances`_ in the *AWS OpsWorks User Guide*.

.. _`Deleting AWS OpsWorks Instances`: http://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances-delete.html


