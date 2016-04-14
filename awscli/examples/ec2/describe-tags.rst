**To describe your tags**

This example describes the tags for all your resources.

Command::

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
              "ResourceId": "vol-1a2b3c4d",
              "Value": "Project1",
              "Key": "Purpose"
          },
          {
              "ResourceType": "volume",
              "ResourceId": "vol-87654321",
              "Value": "Logs",
              "Key": "Purpose"
          }
      ]
  }

**To describe the tags for a single resource**

This example describes the tags for the specified instance.

Command::

  aws ec2 describe-tags --filters "Name=resource-id,Values=i-1234567890abcdef8"

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

**To describe the tags for a type of resource**

This example describes the tags for your volumes.

Command::

  aws ec2 describe-tags --filters "Name=resource-type,Values=volume"

Output::

  {
      "Tags": [
          {
              "ResourceType": "volume",
              "ResourceId": "vol-1a2b3c4d",
              "Value": "Project1",
              "Key": "Purpose"
          },
          {
              "ResourceType": "volume",
              "ResourceId": "vol-87654321",
              "Value": "Logs",
              "Key": "Purpose"
          }
      ]
  }

**To describe the tags for your resources based on a key and a value**

This example describes the tags for your resources that have the key ``Stack`` and a value ``Test``.

Command::

  aws ec2 describe-tags --filters "Name=key,Values=Stack" "Name=value,Values=Test"

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

This example describes the tags for all your instances that have a tag with the key ``Purpose`` and no value.

Command::

    aws ec2 describe-tags --filters "Name=resource-type,Values=instance" "Name=key,Values=Purpose" "Name=value,Values="
    
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

