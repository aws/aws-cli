**To get the contents of a configuration document**

This example gets the contents of the document called ``My_Config_Document``.

Command::

  aws ssm get-document --name "My_Config_Document"


Output::

 {
     "Content": "{\n
   \"schemaVersion\": \"1.0\",\n
   \"description\": \"Sample configuration to join an instance to a domain\",\n
   \"runtimeConfig\": {\n
     \"aws:domainJoin\": {\n
        \"properties\": [\n
          {\n
            \"directoryId\": \"d-1234567890\",\n
            \"directoryName\": \"test.example.com\",\n
            \"dnsIpAddresses\": [\"198.51.100.1\",\"198.51.100.2\"]\n
          }\n
        ]\n
     }\n
   }\n
 }", 
     "Name": "My_Config_Document"
 }