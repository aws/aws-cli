**To upload documents to an Amazon CloudSearch domain**

The following ``upload-documents`` example uploads a batch of JSON documents to an Amazon CloudSearch domain. ::

    aws cloudsearchdomain upload-documents \
        --endpoint-url https://doc-my-domain.us-west-2.cloudsearch.amazonaws.com \
        --content-type application/json \
        --documents document-batch.json

Output::

    {
        "status": "success",
        "adds": 5000,
        "deletes": 0
    }

For more information, see `Uploading Data to an Amazon CloudSearch Domain <https://docs.aws.amazon.com/cloudsearch/latest/developerguide/uploading-data.html>`__ in the *Amazon CloudSearch Developer Guide*.
