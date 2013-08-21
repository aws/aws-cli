**To rename an IAM group**

The following ``update-group`` commmand changes the name of the IAM group ``Test`` to ``Test-1``::

  aws iam update-group --group-name Test --new-group-name Test-1

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Renaming Users and Groups`_ in the *Using IAM* guide.

