**To list tags associated with an App Runner service**

The following ``list-tags-for-resource`` example lists all the tags that are associated with an App Runner service. ::

    aws apprunner list-tags-for-resource \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "ResourceArn": "arn:aws:apprunner:us-west-2:123456789012:service/python-app/8fe1e10304f84fd2b0df550fe98a71fa"
    }

Output::

    {
        "Tags": [
            {
                "Key": "Department", 
                "Value": "Retail"
            },
            {
                "Key": "CustomerId", 
                "Value": "56439872357912"
            }
        ]
    }

For more information, see `Configuring an App Runner service <https://docs.aws.amazon.com/apprunner/latest/dg/manage-configure.html>`__ in the *AWS App Runner Developer Guide*.
