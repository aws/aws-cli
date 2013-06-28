**To activate or deactivate an access key for an IAM user**

The following ``update-access-key`` commmand deactivates the specified access key (access key ID and secret access key) for the IAM user named ``Bob``::

  aws iam update-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --status Inactive --user-name Bob

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Creating, Modifying, and Viewing User Security Credentials`_ in the *Using IAM* guide.
 
.. _Creating, Modifying, and Viewing User Security Credentials: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_CreateAccessKey.html


