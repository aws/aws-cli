**Example 1: To list all of the resources in a resource group**

The following ``list-group-resources`` example lists all of the resources that are part of the specified resource group. ::

    aws resource-groups list-group-resources \
        --group-name tbq-WebServer

Output::

    {
        "ResourceIdentifiers": [
            {
                "ResourceArn": "arn:aws:ec2:us-west-2:123456789012:instance/i-09f77fa38c12345ab",
                "ResourceType": "AWS::EC2::Instance"
            }
        ]
    }

**Example 2: To list the resources of a specific type in a resource group**

The following ``list-group-resources`` example lists all of the resources in the group that also have a ``resource-type`` of ``AWS::EC2::Instance``. ::

    aws resource-groups list-group-resources \
        --group-name tbq-WebServer \
        --filters Name=resource-type,Values=AWS::EC2::Instance

Output::

    {
        "ResourceIdentifiers": [
            {
                "ResourceArn": "arn:aws:ec2:us-west-2:123456789012:instance/i-09f77fa38c12345ab",
                "ResourceType": "AWS::EC2::Instance"
            }
        ]
    }

For more information, see `What are resource groups? <https://docs.aws.amazon.com/ARG/latest/userguide/resource-groups.html>`__ in the *AWS Resource Groups User Guide*.
