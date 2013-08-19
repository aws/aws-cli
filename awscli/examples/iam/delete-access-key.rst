**To delete an access key for an IAM user**

The following ``delete-access-key`` commmand deletes the specified access key (access key ID and secret access key) for the IAM user named ``Bob``::

  aws iam delete-access-key --access-key AKIDPMS9RO4H3FEXAMPLE --user-name Bob

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

To list the access keys defined for an IAM user, use the ``list-access-keys`` command.

For more information, see `Creating, Modifying, and Viewing User Security Credentials`_ in the *Using IAM* guide.

.. _Creating, Modifying, and Viewing User Security Credentials: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_CreateAccessKey.html


