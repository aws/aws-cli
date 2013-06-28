**To delete an IAM user**

The following ``delete-user`` commmand removes the IAM user named ``Bob`` from the current account::

  aws iam delete-user --user-name Bob

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    
  
For more information, see `Deleting a User from Your AWS Account`_ in the *Using IAM* guide.

.. _Deleting a User from Your AWS Account: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_DeletingUserFromAccount.html

