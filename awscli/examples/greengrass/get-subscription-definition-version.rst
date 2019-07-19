**To retrieve information about a specific version of a subscription definition**

The following ``get-subscription-definition-version`` example retrieves information about the specified version of the specified subscription definition. You can use the ``get-subscription-definition`` command to get the latest subscription definition version ID. To get the ID of another version, you can use the ``list-subscription-definition-versions`` command. ::

    aws greengrass get-subscription-definition-version \
        --subscription-definition-id "70e49321-83d5-45d2-bc09-81f4917ae152" \
        --subscription-definition-version-id "88ae8699-12ac-4663-ba3f-4d7f0519140b"
    
Output::

   {
       "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/70e49321-83d5-45d2-bc09-81f4917ae152/versions/88ae8699-12ac-4663-ba3f-4d7f0519140b",
       "CreationTimestamp": "2019-06-18T17:03:52.499Z",
       "Definition": {
           "Subscriptions": [
               {
                   "Id": "692c4484-d89f-4f64-8edd-1a041a65e5b6",
                   "Source": "arn:aws:lambda:us-west-2:123456789012:function:Greengrass_HelloWorld:GG_HelloWorld",
                   "Subject": "hello/world",
                   "Target": "cloud"
               }
           ]
       },
       "Id": "70e49321-83d5-45d2-bc09-81f4917ae152",
       "Version": "88ae8699-12ac-4663-ba3f-4d7f0519140b"
   }
