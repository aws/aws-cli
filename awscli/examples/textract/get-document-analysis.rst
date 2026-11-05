**To get the results of asynchronous text analysis of a multi-page document**

The following ``get-document-analysis`` example shows how to get the results of asynchronous text analysis of a multi-page document. ::

    aws textract get-document-analysis \
        --job-id df7cf32ebbd2a5de113535fcf4d921926a701b09b4e7d089f3aebadb41e0712b \
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
        "NextToken": "cY1W3eTFvoB0cH7YrKVudI4Gb0H8J0xAYLo8xI/JunCIPWCthaKQ+07n/ElyutsSy0+1VOImoTRmP1zw4P0RFtaeV9Bzhnfedpx1YqwB4xaGDA==", 
        "DocumentMetadata": {
            "Pages": 1
        }, 
        "JobStatus": "SUCCEEDED"
    }

For more information, see `Processing Documents Asynchronously <https://docs.aws.amazon.com/textract/latest/dg/async.html>`__ in the *Amazon Textract Developer Guide*.
