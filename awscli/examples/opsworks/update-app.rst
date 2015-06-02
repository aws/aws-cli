**To update an app**

The following example updates a specified app to change its name. ::

  aws opsworks --region us-east-1 update-app --app-id 26a61ead-d201-47e3-b55c-2a7c666942f8 --name NewAppName

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Editing Apps`_ in the *AWS OpsWorks User Guide*.

.. _`Editing Apps`: http://docs.aws.amazon.com/opsworks/latest/userguide/workingapps-editing.html

