**To update image set metadata**

The following ``update-image-set-metadata`` code example updates image set metadata. ::

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
        "latestVersionId": "5",
        "imageSetWorkflowStatus": "UPDATING",
        "updatedAt": 1680042257.908,
        "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
        "imageSetState": "LOCKED",
        "createdAt": 1680027126.436,
        "datastoreId": "12345678901234567890123456789012"
    }

For more information, see `Updating image set metadata <https://docs.aws.amazon.com/healthimaging/latest/devguide/update-image-set-metadata.html>`__ in the *AWS HealthImaging Developer Guide*.
