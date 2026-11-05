**To create an application**

The following ``create-application`` example creates an application and associates it with the user's AWS account. ::

    aws deploy create-application \
        --application-name MyOther_App

Output::

    {
        "applicationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Create an application with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/applications-create.html>`__ in the *AWS CodeDeploy User Guide*.
