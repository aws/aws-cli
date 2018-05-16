**To add or delete tags for a health check or hosted zone**

The following ``change-tags-for-resource`` command adds and deletes tags using the settings in the file ``change-tags-for-resource.json`` (you can use any name for the file)::

  aws route53 change-tags-for-resource --cli-input-json file://C:\temp\change-tags-for-resource.json

You can add and delete tags in only one health check or one hosted zone at a time.

To change the value for a key, just include the key and the new value under ``AddTags``.

Here's the syntax for the file that contains the tags that you want to add and delete::

  {
    "ResourceType": "healthcheck"|"hostedzone",
    "ResourceId": "string",
    "AddTags": [
      {
        "Key": "string",
        "Value": "string"
      },
	  ...
    ],
    "RemoveTagKeys": [
      "string",
	  ...
    ]
  }