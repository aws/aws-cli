**To get the results of asynchronous text detection in a multi-page document**

The following ``get-document-text-detection`` example shows how to get the results of asynchronous text detection in a multi-page document. ::

    aws textract get-document-text-detection \
        --job-id 57849a3dc627d4df74123dca269d69f7b89329c870c65bb16c9fd63409d200b9 \
        --max-results 1000

Output::

    {
        "Blocks": [
            {
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1.0, 
                        "Top": 0.0, 
                        "Left": 0.0, 
                        "Height": 1.0
                    }, 
                    "Polygon": [
                        {
                            "Y": 0.0, 
                            "X": 0.0
                        }, 
                        {
                            "Y": 0.0, 
                            "X": 1.0
                        }, 
                        {
                            "Y": 1.0, 
                            "X": 1.0
                        }, 
                        {
                            "Y": 1.0, 
                            "X": 0.0
                        }
                    ]
                }, 
                "Relationships": [
                    {
                        "Type": "CHILD", 
                        "Ids": [
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
                        ]
                    }
                ], 
                "BlockType": "PAGE", 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444", 
                "Page": 1
            }
        ], 
        "NextToken": "GcqyoAJuZwujOT35EN4LCI3EUzMtiLq3nKyFFHvU5q1SaIdEBcSty+njNgoWwuMP/muqc96S4o5NzDqehhXvhkodMyVO5OJGyms5lsrCxibWJw==", 
        "DocumentMetadata": {
            "Pages": 1
        }, 
        "JobStatus": "SUCCEEDED"
    }

For more information, see `Processing Documents Asynchronously <https://docs.aws.amazon.com/textract/latest/dg/async.html>`__ in the *Amazon Textract Developer Guide*.
