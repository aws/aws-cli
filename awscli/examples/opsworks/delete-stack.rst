**To delete a stack**

The following example deletes a specified stack, which is identified by its stack ID.
You can obtain a stack ID by clicking **Stack Settings** on the AWS OpsWorks console or by
running the ``describe-stacks`` command.

**Note:** Before deleting a layer, you must use ``delete-app``, ``delete-instance``, and ``delete-layer``
to delete all of the stack's apps, instances, and layers. ::

  aws opsworks delete-stack --region us-east-1 --stack-id 154a9d89-7e9e-433b-8de8-617e53756c84

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Shut Down a Stack`_ in the *AWS OpsWorks User Guide*.

.. _`Shut Down a Stack`: http://docs.aws.amazon.com/opsworks/latest/userguide/workingstacks-shutting.html
