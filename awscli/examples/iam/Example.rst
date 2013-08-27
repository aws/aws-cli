**To add an IAM user to a group**

The following ``add-user-to-group`` command adds the user MyUser to the group MyIamGroup::

  aws iam add-user-to-group --user-name MyUser --group-name MyIamGroup

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }

For more information, see `Create New IAM Users and Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Create New IAM Users and Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-iam-new-user-group.html
