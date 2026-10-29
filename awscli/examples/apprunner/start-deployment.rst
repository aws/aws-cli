**To initiate a manual deployment**

The following ``start-deployment`` example performs a manual deployment to an App Runner service. ::

    aws apprunner start-deployment \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "ServiceArn": "arn:aws:apprunner:us-west-2:123456789012:service/python-app/8fe1e10304f84fd2b0df550fe98a71fa"
    }

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Deploying a new application version to App Runner <https://docs.aws.amazon.com/apprunner/latest/dg/manage-deploy.html>`__ in the *AWS App Runner Developer Guide*.
