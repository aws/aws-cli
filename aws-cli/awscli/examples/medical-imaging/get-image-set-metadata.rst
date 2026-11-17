**Example 1: To get image set metadata without version**

The following ``get-image-set-metadata`` example gets metadata for an image set without specifying a version.

Note: ``outfile`` is a required parameter. ::

    aws medical-imaging get-image-set-metadata studymetadata.json.gz \
        --datastore-id 12345678901234567890123456789012 \
        --image-set-id ea92b0d8838c72a3f25d00d13616f87e

The returned metadata is compressed with gzip and stored in the studymetadata.json.gz file. To view the contents of the returned JSON object, you must first decompress it.

Output::

    {
        "contentType": "application/json",
        "contentEncoding": "gzip"
    }

**Example 2: To get image set metadata with version**

The following ``get-image-set-metadata`` example gets metadata for an image set with a specified version.

Note: ``outfile`` is a required parameter. ::

    aws medical-imaging get-image-set-metadata studymetadata.json.gz \
        --datastore-id 12345678901234567890123456789012 \
        --image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --version-id 1

The returned metadata is compressed with gzip and stored in the studymetadata.json.gz file. To view the contents of the returned JSON object, you must first decompress it.

Output::

    {
        "contentType": "application/json",
        "contentEncoding": "gzip"
    }

For more information, see `Getting image set metadata <https://docs.aws.amazon.com/healthimaging/latest/devguide/get-image-set-metadata.html>`__ in the *AWS HealthImaging Developer Guide*.
