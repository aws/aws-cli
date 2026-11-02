**To get information about multiple applications**

The following ``batch-get-applications`` example displays information about multiple applications that are associated with the user's AWS account. ::

    aws deploy batch-get-applications \
        --application-names WordPress_App MyOther_App

Output::

    {
        "applicationsInfo": [
            {
                "applicationName": "WordPress_App",
                "applicationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "createTime": 1407878168.078,
                "linkedToGitHub": false
            },
            {
                "applicationName": "MyOther_App",
                "applicationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "createTime": 1407453571.63,
                "linkedToGitHub": false
            }
        ]
    }

For more information, see `View application details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/applications-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
