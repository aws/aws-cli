**To list the tags associated with an application**

This command uses the ``list-tags-for-resource`` command to retrieve a list of the tags associated with a specified application. ::

    aws application-insights list-tags-for-resource \
        --resource-arn arn:aws:applicationinsights:eu-west-1:123456789012:application/resource-group/myapp

Output::

    {
        "Tags": [{
            "Key": "AWS",
            "Value": "tagaws"
        }]
    }