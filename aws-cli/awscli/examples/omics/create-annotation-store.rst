**Example 1: To create a VCF annotation store**

The following ``create-annotation-store`` example creates a VCF format annotation store. ::

    aws omics create-annotation-store \
        --name my_ann_store \
        --store-format VCF \
        --reference referenceArn=arn:aws:omics:us-west-2:123456789012:referenceStore/1234567890/reference/1234567890

Output::

    {
        "creationTime": "2022-11-23T22:48:39.226492Z",
        "id": "0a91xmplc71f",
        "name": "my_ann_store",
        "reference": {
            "referenceArn": "arn:aws:omics:us-west-2:123456789012:referenceStore/1234567890/reference/1234567890"
        },
        "status": "CREATING",
        "storeFormat": "VCF"
    }

For more information, see `Creating HealthOmics annotation stores <https://docs.aws.amazon.com/omics/latest/dev/creating-and-managing-annotation-store.html>`__ in the *AWS HealthOmics User Guide*.

**Example 2: To create a TSV annotation store**

The following ``create-annotation-store`` example creates a TSV format annotation store. ::

    aws omics create-annotation-store \
        --name tsv_ann_store \
        --store-format TSV \
        --reference referenceArn=arn:aws:omics:us-west-2:123456789012:referenceStore/1234567890/reference/1234567890 \
        --store-options file://tsv-store-options.json

The ``tsv-store-options.json`` file configures format options for annotations.

Contents of ``tsv-store-options.json``::

    {
        "tsvStoreOptions": {
            "annotationType": "CHR_START_END_ZERO_BASE",
            "formatToHeader": {
                "CHR": "chromosome",
                "START": "start",
                "END": "end"
            },
            "schema": [
                {
                    "chromosome": "STRING"
                },
                {
                    "start": "LONG"
                },
                {
                    "end": "LONG"
                },
                {
                    "name": "STRING"
                }
            ]
        }
    }

Output::

    {
        "creationTime": "2022-11-30T01:28:08.525586Z",
        "id": "861cxmpl96b0",
        "name": "tsv_ann_store",
        "reference": {
            "referenceArn": "arn:aws:omics:us-west-2:123456789012:referenceStore/1234567890/reference/1234567890"
        },
        "status": "CREATING",
        "storeFormat": "TSV",
        "storeOptions": {
            "tsvStoreOptions": {
                "annotationType": "CHR_START_END_ZERO_BASE",
                "formatToHeader": {
                    "CHR": "chromosome",
                    "END": "end",
                    "START": "start"
                },
                "schema": [
                    {
                        "chromosome": "STRING"
                    },
                    {
                        "start": "LONG"
                    },
                    {
                        "end": "LONG"
                    },
                    {
                        "name": "STRING"
                    }
                ]
            }
        }
    }

For more information, see `Creating HealthOmics annotation stores <https://docs.aws.amazon.com/omics/latest/dev/creating-and-managing-annotation-store.html>`__ in the *AWS HealthOmics User Guide*.
