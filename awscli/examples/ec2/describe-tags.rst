**Example 1: To describe your tags**

The following ``describe-tags`` example describes the tags for all your resources. ::

    aws ec2 describe-tags

Output::

    {
        "Tags": [
            {
                "ResourceType": "image",
                "ResourceId": "ami-78a54011",
                "Value": "Production",
                "Key": "Stack"
            },
            {
                "ResourceType": "image",
                "ResourceId": "ami-3ac33653",
                "Value": "Test",
                "Key": "Stack"
            },
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef0",
                "Value": "Production",
                "Key": "Stack"
            },
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef1",
                "Value": "Test",
                "Key": "Stack"
            },
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef5",
                "Value": "Beta Server",
                "Key": "Name"
            },
            {
                "ResourceType": "volume",
                "ResourceId": "vol-049df61146c4d7901",
                "Value": "Project1",
                "Key": "Purpose"
            },
            {
                "ResourceType": "volume",
                "ResourceId": "vol-1234567890abcdef0",
                "Value": "Logs",
                "Key": "Purpose"
            }
        ]
    }

**Example 2: To describe the tags for a single resource**

The following ``describe-tags`` example describes the tags for the specified instance. ::

    aws ec2 describe-tags \
        --filters "Name=resource-id,Values=i-1234567890abcdef8"

Output::

    {
        "Tags": [
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef8",
                "Value": "Test",
                "Key": "Stack"
            },
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef8",
                "Value": "Beta Server",
                "Key": "Name"
            }
        ]
    }

**Example 3: To describe the tags for a type of resource**

The following ``describe-tags`` example describes the tags for your volumes. ::

    aws ec2 describe-tags \
        --filters "Name=resource-type,Values=volume"

Output::

    {
        "Tags": [
            {
                "ResourceType": "volume",
                "ResourceId": "vol-1234567890abcdef0",
                "Value": "Project1",
                "Key": "Purpose"
            },
            {
                "ResourceType": "volume",
                "ResourceId": "vol-049df61146c4d7901",
                "Value": "Logs",
                "Key": "Purpose"
            }
        ]
    }

**Example 4: To describe the tags for your resources based on a key and a value**

The following ``describe-tags`` example describes the tags for your resources that have the key ``Stack`` and a value ``Test``. ::

    aws ec2 describe-tags \
        --filters "Name=key,Values=Stack" "Name=value,Values=Test"

Output::

    {
        "Tags": [
            {
                "ResourceType": "image",
                "ResourceId": "ami-3ac33653",
                "Value": "Test",
                "Key": "Stack"
            },
            {
                "ResourceType": "instance",
                "ResourceId": "i-1234567890abcdef8",
                "Value": "Test",
                "Key": "Stack"
            }
        ]
    }

**Example 5: To describe the tags for your resources based on a key and a value using the shortcut syntax**

The following ``describe-tags`` example is an alternative syntax to describe resources with the key ``Stack`` and a value ``Test``. ::

    aws ec2 describe-tags --filters "Name=tag:Stack,Values=Test"

**Example 6: To describe the tags for your resources based on only a key**

This example describes the tags for all your instances that have a tag with the key ``Purpose`` and no value. ::

    aws ec2 describe-tags \
        --filters "Name=resource-type,Values=instance" "Name=key,Values=Purpose" "Name=value,Values="

Output::

    {
        "Tags": [
            {
                "ResourceType": "instance", 
                "ResourceId": "i-1234567890abcdef5", 
                "Value": null, 
                "Key": "Purpose"
            }
        ]
    }

