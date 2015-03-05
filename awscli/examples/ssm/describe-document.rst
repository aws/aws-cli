**To describe a configuration document**

This example returns information about a document called ``My_Config_Doc``.

Command::

  aws ssm describe-document --name "My_Config_Doc"
  
Output::

   {
    "Document": {
        "Status": "Active", 
        "Sha1": "715919de171exampleb3d803025817856844a5f3", 
        "Name": "My_Config_Doc", 
        "CreatedDate": 1424351175.521
    }
   }


