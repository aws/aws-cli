**To change an IAM user's name**

The following ``update-user`` commmand changes the name of the IAM user ``Bob`` to ``Robert``::

  aws iam update-user --user-name Bob --new-user-name Robert

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Renaming Users and Groups`_ in the *Using IAM* guide.
 
.. _Renaming Users and Groups: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_Renaming.html
 
