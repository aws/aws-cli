**To remove permissions from a resource**

The following ``remove-resource-permission`` example removes permissions from the resource for the specified principal. This command produces no output. ::

    aws workdocs remove-resource-permission \
        --resource-id 1ece93e5fe75315c7407c4967918b4fd9da87ddb2a588e67b7fdaf4a98fde678 \
        --principal-id anonymous
