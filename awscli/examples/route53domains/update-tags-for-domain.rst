**To add or update tags for a domain**

The following ``update-tags-for-domain`` command adds or updates tags using the settings in the file ``update-tags-for-domain.json`` (you can use any name for the file)::

  aws route53domains update-tags-for-domain --region us-east-1 --domain-name example.com --cli-input-json file://C:\temp\update-tags-for-domain.json

If the default region is us-east-1, you can omit the ``region`` parameter.

You can add or update tags in only one domain at a time.

To change the value for a key, just include the key and the new value.

Here's the syntax for the file that contains the tags that you want to add or update::

  {
    "TagsToUpdate":[
      {
        "Key": "string",
        "Value": "string"
      },
	  ...
    ]
  }