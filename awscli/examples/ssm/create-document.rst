**To create a configuration document**

This example creates a configuration document called ``My_Document`` in your account. The document must be in JSON format. For more information about writing a configuration document, see `Configuration Document`_ in the *SSM API Reference*.

.. _`Configuration Document`: http://docs.aws.amazon.com/ssm/latest/APIReference/aws-ssm-document.html

Command::

  aws ssm create-document --content file://myconfigfile.json --name "My_Config_Document"

Output::

 {
    "DocumentDescription": {
        "Status": "Creating", 
        "Sha1": "715919de1715exampled803025817856844a5f3", 
        "Name": "My_Config_Document", 
        "CreatedDate": 1424351175.521
    }
 }


