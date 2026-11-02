**To remove tags from an App Runner service**

The following ``untag-resource`` example removes two tags from an App Runner service. ::

    aws apprunner untag-resource \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "ResourceArn": "arn:aws:apprunner:us-west-2:123456789012:service/python-app/8fe1e10304f84fd2b0df550fe98a71fa",
        "TagKeys": [
            "Department", 
            "CustomerId"
        ]
    }

This command produces no output.

For more information, see `Authorization based on App Runner tags <https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html#security_iam_service-with-iam-tags>`__ in the *AWS App Runner Developer Guide*.
