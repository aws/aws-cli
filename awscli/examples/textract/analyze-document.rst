**To analyze text in a document**

The following ``analyze-document`` example shows how to analyze text in a document.

For Linux and macOS, use the following command. ::

    aws textract analyze-document \
        --document '{"S3Object":{"Bucket":"amzn-s3-demo-bucket","Name":"document"}}' \
        --feature-types '["TABLES","FORMS"]'

For Windows, use the following command. ::

    aws textract analyze-document \
        --document "{\"S3Object\":{\"Bucket\":\"amzn-s3-demo-bucket\",\"Name\":\"document\"}}" \
        --feature-types "[\"TABLES\",\"FORMS\"]"

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
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            }
        ], 
        "DocumentMetadata": {
            "Pages": 1
        }
    }

For more information, see `Analyzing Document Text with Amazon Textract <https://docs.aws.amazon.com/textract/latest/dg/analyzing-document-text.html>`__ in the *Amazon Textract Developer Guide*.
