**Example 1: To run a workflow**

The following ``start-run`` example runs a workflow with ID ``1234567``. ::

    aws omics start-run \
        --workflow-id 1234567 \
        --role-arn arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ \
        --name 'cram-to-bam' \
        --output-uri s3://amzn-s3-demo-bucket/workflow-output/ \
        --run-group-id 1234567 \
        --priority 1 \
        --storage-capacity 10 \
        --log-level ALL \
        --parameters file://workflow-inputs.json

Contents of ``workflow-inputs.json``::

    {
        "sample_name": "NA12878",
        "input_cram": "s3://amzn-s3-demo-bucket/NA12878.cram",
        "ref_dict": "s3://amzn-s3-demo-bucket/Homo_sapiens_assembly38.dict",
        "ref_fasta": "s3://amzn-s3-demo-bucket/Homo_sapiens_assembly38.fasta",
        "ref_fasta_index": "amzn-s3-demo-bucket/Homo_sapiens_assembly38.fasta.fai"
    }

Output::

    {
        "arn": "arn:aws:omics:us-west-2:123456789012:run/1234567",
        "id": "1234567",
        "status": "PENDING",
        "tags": {}
    }

For more information, see `Starting a run <https://docs.aws.amazon.com/omics/latest/dev/starting-a-run.html>`__ in the *AWS HealthOmics User Guide*.

**Example 2: To load source files from Amazon Omics**

The following ``start-run`` example loads source files from Amazon Omics storage by using service-specific URIs. The ``workflow-inputs.json`` file for this example uses Amazon Omics URIs for read set and reference genome sources. ::

    {
        "sample_name": "NA12878",
        "input_cram": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/readSet/1234567890/source1",
        "ref_dict": "s3://amzn-s3-demo-bucket/Homo_sapiens_assembly38.dict",
        "ref_fasta": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/reference/1234567890",
        "ref_fasta_index": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/reference/1234567890/index"
    }

