**To create an IAM group**

The following ``create-group`` command creates an IAM group named ``Admins``::

  aws iam create-group --group-name Admins

Output::

  {
    "Group": {
        "Path": "/",
        "CreateDate": "2013-06-04T20:27:27.972Z",
        "GroupId": "AIDGPMS9RO4H3FEXAMPLE",
        "Arn": "arn:aws:iam::123456789012:group/Admins",
        "GroupName": "Admins"
    }
  }

For more information, see `Creating and Listing Groups`_ in the *Using IAM* guide.

.. _`Creating and Listing Groups`: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_CreatingAndListingGroups.html

