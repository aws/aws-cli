**Example 1: To create a data store**

The following ``create-datastore`` code example creates a data store with the name ``my-datastore``.
When you create a datastore without specifying a ``--lossless-storage-format``, AWS HealthImaging defaults to HTJ2K (High Throughput JPEG 2000). ::

    aws medical-imaging create-datastore \
        --datastore-name "my-datastore"

Output::

    {
        "datastoreId": "12345678901234567890123456789012",
        "datastoreStatus": "CREATING"
    }

**Example 2: To create a data store with JPEG 2000 Lossless storage format**

A data store configured with JPEG 2000 Lossless storage format will transcode and persist lossless image frames in JPEG 2000 format. Image frames can then be retrieved in 
JPEG 2000 Lossless without transcoding. The following ``create-datastore`` code example creates a data store configured for JPEG 2000 Lossless storage format with the name ``my-datastore``. ::

    aws medical-imaging create-datastore \
        --datastore-name "my-datastore" \
        --lossless-storage-format JPEG_2000_LOSSLESS

Output::

    {
        "datastoreId": "12345678901234567890123456789012",
        "datastoreStatus": "CREATING"
    }

For more information, see `Creating a data store <https://docs.aws.amazon.com/healthimaging/latest/devguide/create-data-store.html>`__ in the *AWS HealthImaging Developer Guide*.
