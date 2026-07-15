**To apply an extension pack to the target database**

The following ``start-extension-pack-association`` example queues the application of an extension pack to the target database. ::

    aws dms start-extension-pack-association \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Using extension packs <https://docs.aws.amazon.com/dms/latest/userguide/extension-pack.html>`__ in the *AWS Database Migration Service User Guide*.
