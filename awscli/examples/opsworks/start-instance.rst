**To start an instance**

The following ``start-instance`` command starts a specified instance::

  aws opsworks start-instance --instance-id f705ee48-9000-4890-8bd3-20eb05825aaf

**Note**: OpsWorks CLI commands should set the region to us-east-1, regardless of the stack's location.

.. _start-stack: http://docs.aws.amazon.com/cli/latest/reference/opsworks/start-stack.html

No output. Use describe-instances_ to check the instance's status.

.. _describe-instances: http://docs.aws.amazon.com/cli/latest/reference/opsworks/describe-instances.html

For more information, see `Adding Apps`_ in the *OpsWorks User Guide*.

.. _`Adding Apps`: http://docs.aws.amazon.com/opsworks/latest/userguide/workingapps-creating.html

**Note**: You can start every offline instance in a stack with one command by calling start-stack_.

