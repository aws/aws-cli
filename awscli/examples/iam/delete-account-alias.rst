**To delete an account alias**

The following ``delete-account-alias`` command removes the alias ``mycompany`` for the current account::

  aws iam delete-account-alias --account-alias mycompany

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Using an Alias for Your AWS Account ID`_ in the *Using IAM* guide.


