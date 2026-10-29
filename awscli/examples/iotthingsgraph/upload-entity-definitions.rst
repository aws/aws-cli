**To upload entity definitions**

The following ``upload-entity-definitions`` example uploads entity definitions to your namespace. The value of ``MyEntityDefinitions`` is the GraphQL that models the entities. ::

    aws iotthingsgraph upload-entity-definitions \
        --document language=GRAPHQL,text="MyEntityDefinitions"

Output::

    {
        "uploadId": "f6294f1e-b109-4bbe-9073-f451a2dda2da"
    }
