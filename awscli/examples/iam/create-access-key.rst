**To create an access key for an IAM user**

The following ``create-access-key`` commmand creates an access key (access key ID and secret access key) for the IAM user named ``Bob``::

  aws iam create-access-key --user-name Bob

Output::

  {
      "AccessKey": {
          "UserName": "Bob",
          "Status": "Active",
          "CreateDate": "2013-06-06T20:42:26.421Z",
          "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY",
          "AccessKeyId": "AKIDPMS9RO4H3FEXAMPLE"
      },
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }

For more information, see `Creating, Modifying, and Viewing User Security Credentials`_ in the *Using IAM* guide.
 
.. _Creating, Modifying, and Viewing User Security Credentials: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_CreateAccessKey.html


