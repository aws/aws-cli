**Example 1: To get a data store's properties**

The following ``get-datastore`` code example gets a data store's properties. ::

    aws medical-imaging get-datastore \
        --datastore-id 12345678901234567890123456789012


Output::

    {
        "datastoreProperties": {
            "datastoreId": "12345678901234567890123456789012",
            "datastoreName": "TestDatastore123",
            "datastoreStatus": "ACTIVE",
            "losslessStorageFormat": "HTJ2K"
            "datastoreArn": "arn:aws:medical-imaging:us-east-1:123456789012:datastore/12345678901234567890123456789012",
            "createdAt": "2022-11-15T23:33:09.643000+00:00",
            "updatedAt": "2022-11-15T23:33:09.643000+00:00"
        }
    }

**Example 2: To get data store's properties configured for JPEG2000** 

The following ``get-datastore`` code example gets a data store's properties for a data store configured for JPEG 2000 Lossless storage format. ::

    aws medical-imaging get-datastore \
        --datastore-id 12345678901234567890123456789012


Output::

    {
        "datastoreProperties": {
            "datastoreId": "12345678901234567890123456789012",
            "datastoreName": "TestDatastore123",
            "datastoreStatus": "ACTIVE",
            "losslessStorageFormat": "JPEG_2000_LOSSLESS",
            "datastoreArn": "arn:aws:medical-imaging:us-east-1:123456789012:datastore/12345678901234567890123456789012",
            "createdAt": "2022-11-15T23:33:09.643000+00:00",
            "updatedAt": "2022-11-15T23:33:09.643000+00:00"
        }
    }

For more information, see `Getting data store properties <https://docs.aws.amazon.com/healthimaging/latest/devguide/get-data-store.html>`__ in the *AWS HealthImaging Developer Guide*.
