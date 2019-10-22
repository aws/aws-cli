**To update the description for a resource group**

The following ``update-group`` example updates the description for a group named ``WebServer3`` in the current region. ::

    aws resource-groups update-group \
        --group-name WebServer3 \
        --description "Group of web server resources."

Output::

    {
        "Group": {
            "GroupArn": "arn:aws:resource-groups:us-east-2:123456789012:group/WebServer3",
            "Name": "WebServer3"
            "Description": "Group of web server resources."
        }
    }
