**To upload entity definitions**

The following ``upload-entity-definitions`` example uploads entity definitions to your namespace. The value of ``MyEntityDefinitions`` is the GraphQL that models the entities. ::

    aws iotthingsgraph upload-entity-definitions \
        --document language=GRAPHQL,text="MyEntityDefinitions"

Output::

    {
        "uploadId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }
