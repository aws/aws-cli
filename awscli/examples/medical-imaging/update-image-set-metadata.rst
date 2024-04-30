**To insert or update an attribute in image set metadata**

The following ``update-image-set-metadata`` code example inserts or updates an attribute in image set metadata. ::

    aws medical-imaging update-image-set-metadata \
        --datastore-id 12345678901234567890123456789012 \
        --image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --latest-version-id 1 \
        --update-image-set-metadata-updates file://metadata-updates.json

Contents of ``metadata-updates.json`` ::

    {
        "DICOMUpdates": {
            "updatableAttributes": "eyJTY2hlbWFWZXJzaW9uIjoxLjEsIlBhdGllbnQiOnsiRElDT00iOnsiUGF0aWVudE5hbWUiOiJNWF5NWCJ9fX0="
        }
    }

Note: ``updatableAttributes`` is a Base64 encoded JSON string. Here is the unencoded JSON string.

{"SchemaVersion":1.1,"Patient":{"DICOM":{"PatientName":"MX^MX"}}}

Output::

    {
        "latestVersionId": "2",
        "imageSetWorkflowStatus": "UPDATING",
        "updatedAt": 1680042257.908,
        "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
        "imageSetState": "LOCKED",
        "createdAt": 1680027126.436,
        "datastoreId": "12345678901234567890123456789012"
    }

**To remove an attribute from image set metadata**

The following ``update-image-set-metadata`` code example removes an attribute from image set metadata. ::

    aws medical-imaging update-image-set-metadata \
        --datastore-id 12345678901234567890123456789012 \
        --image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --latest-version-id 1 \
        --update-image-set-metadata-updates file://metadata-updates.json

Contents of ``metadata-updates.json`` ::

    {
        "DICOMUpdates": {
            "removableAttributes": "e1NjaGVtYVZlcnNpb246MS4xLFN0dWR5OntESUNPTTp7U3R1ZHlEZXNjcmlwdGlvbjpDSEVTVH19fQo="
        }
    }

Note: ``removableAttributes`` is a Base64 encoded JSON string. Here is the unencoded JSON string. The key and value must match the attribute to be removed.

{"SchemaVersion":1.1,"Study":{"DICOM":{"StudyDescription":"CHEST"}}}

Output::

    {
        "latestVersionId": "2",
        "imageSetWorkflowStatus": "UPDATING",
        "updatedAt": 1680042257.908,
        "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
        "imageSetState": "LOCKED",
        "createdAt": 1680027126.436,
        "datastoreId": "12345678901234567890123456789012"
    }

**To remove an instance from image set metadata**

The following ``update-image-set-metadata`` code example removes an instance from image set metadata. ::

    aws medical-imaging update-image-set-metadata \
        --datastore-id 12345678901234567890123456789012 \
        --image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --latest-version-id 1 \
        --update-image-set-metadata-updates file://metadata-updates.json

Contents of ``metadata-updates.json`` ::

    {
        "DICOMUpdates": {
            "removableAttributes": "eezEuMS4xLjEuMS4xLjEyMzQ1LjEyMzQ1Njc4OTAxMi4xMjMuMTIzNDU2Nzg5MDEyMzQuMTp7SW5zdGFuY2VzOnsxLjEuMS4xLjEuMS4xMjM0NS4xMjM0NTY3ODkwMTIuMTIzLjEyMzQ1Njc4OTAxMjM0LjE6e319fX19fQo="
        }
    }

Note: ``removableAttributes`` is a Base64 encoded JSON string. Here is the unencoded JSON string.

{"1.1.1.1.1.1.12345.123456789012.123.12345678901234.1":{"Instances":{"1.1.1.1.1.1.12345.123456789012.123.12345678901234.1":{}}}}}}

Output::

    {
        "latestVersionId": "2",
        "imageSetWorkflowStatus": "UPDATING",
        "updatedAt": 1680042257.908,
        "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
        "imageSetState": "LOCKED",
        "createdAt": 1680027126.436,
        "datastoreId": "12345678901234567890123456789012"
    }

For more information, see `Updating image set metadata <https://docs.aws.amazon.com/healthimaging/latest/devguide/update-image-set-metadata.html>`__ in the *AWS HealthImaging Developer Guide*.
