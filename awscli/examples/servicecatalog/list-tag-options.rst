**To list all TagOptions**

The following ``list-tag-options`` example lists all values for ``TagOptions``. ::

    aws servicecatalog list-tag-options 

Output::

    {
        "TagOptionDetails": [
            {
                "Value": "newvalue",
                "Active": true,
                "Id": "tag-iabcdn4fzjjms",
                "Key": "1234"
            },
            {
                "Value": "value1",
                "Active": true,
                "Id": "tag-e3abcdvmwvrzy",
                "Key": "key"
            }
        ]
    }

For more information, see `AWS Service Catalog TagOption Library <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/tagoptions.html>`__ in the *AWS Service Catalog Administrator Guide*.
