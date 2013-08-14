**To create an IAM group**

The following ``create-group`` command creates a new IAM group called MyIamGroup::

    aws iam create-group --group-name MyIamGroup

    {
        "Group": {
            "GroupName": "MyIamGroup",
            "CreateDate": "2012-12-20T03:03:52.834Z",
            "GroupId": "AGPAIGY6KL24AOI54PUQM",
            "Arn": "arn:aws:iam::123456789012:group/MyIamGroup",
            "Path": "/"
        },
        "ResponseMetadata": {
            "RequestId": "e27b3dff-4a51-11e2-b0d6-01979257b0da"
        }
    }    

For more information, see `Create New IAM Users and Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Create New IAM Users and Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-iam-new-user-group.html

