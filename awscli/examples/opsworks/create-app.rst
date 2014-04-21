**To create an app**

The following ``create-app`` command creates a PHP app named SimplePHPApp from code stored on a GitHub repository::

  aws opsworks --region us-east-1 create-app --stack-id f6673d70-32e6-4425-8999-265dd002fec7 --name SimplePHPApp --type php --app-source Type=git,Url=git://github.com/amazonwebservices/opsworks-demo-php-simple-app.git,Revision=version1

**Note**: OpsWorks CLI commands should set the region to us-east-1, regardless of the stack's location.

Output::

  {
    "AppId": "6cf5163c-a951-444f-a8f7-3716be75f2a2"
  }

For more information, see `Adding Apps`_ in the *OpsWorks User Guide*.

.. _`Adding Apps`: http://docs.aws.amazon.com/opsworks/latest/userguide/workingapps-creating.html

