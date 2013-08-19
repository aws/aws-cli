**To get information about an IAM user**

The following ``get-user`` commmand gets information about the IAM user named ``Bob``::

  aws iam get-user --user-name Bob

Output::

  {
      "User": {
          "UserName": "Bob",
          "Path": "/",
          "CreateDate": "2012-09-21T23:03:13Z",
          "UserId": "AKIAIOSFODNN7EXAMPLE",
          "Arn": "arn:aws:iam::123456789012:user/Bob"
      },
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }

For more information, see `Listing Users`_ in the *Using IAM* guide.
 
.. _Listing Users: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_GetListOfUsers.html
 
 
