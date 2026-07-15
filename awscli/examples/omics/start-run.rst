**To run a workflow**

The following ``start-run`` example runs a workflow with ID ``1234567``. ::

    aws omics start-run \
        --workflow-id 1234567 \
        --role-arn arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ \
        --name 'cram-to-bam' \
        --output-uri s3://omics-artifacts-01d6xmpl4e72dd32/workflow-output/ \
        --run-group-id 1234567 \
        --priority 1 \
        --storage-capacity 10 \
        --log-level ALL \
        --parameters file://workflow-inputs.json

`workflow-inputs.json` is a JSON document with the following content. ::

    {
        "sample_name": "NA12878",
        "input_cram": "s3://omics-artifacts-01d6xmpl4e72dd32/NA12878.cram",
        "ref_dict": "s3://omics-artifacts-01d6xmpl4e72dd32/Homo_sapiens_assembly38.dict",
        "ref_fasta": "s3://omics-artifacts-01d6xmpl4e72dd32/Homo_sapiens_assembly38.fasta",
        "ref_fasta_index": "omics-artifacts-01d6xmpl4e72dd32/Homo_sapiens_assembly38.fasta.fai"
    }

Output::

    {
        "arn": "arn:aws:omics:us-west-2:123456789012:run/1234567",
        "id": "1234567",
        "status": "PENDING",
        "tags": {},
        "uuid": "12345678-1234-1234-1234-123456789012",
        "runOutputUri": "s3://omics-output-bucket/workflow-results/"
    }

**To run a shared workflow**

The following example demonstrates how to use ``start-run`` with a shared workflow. ::

    aws omics start-run \
        --workflow-id 1234567 \
        --workflow-owner-id 123456789012 \
        --role-arn arn:aws:iam::123456789012:role/HealthOmicsServiceRole \
        --output-uri s3://your-bucket/results/ \
        --parameters '{
            "param1": "value1", 
            "param2": "value2"
            }'

Output::

    {
        "arn": "arn:aws:omics:us-east-1:123456789012:run/1234567",
        "id": "1234567",
        "status": "PENDING",
        "tags": {},
        "uuid": "a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
        "runOutputUri": "s3://your-bucket/results/1234567"
    }

**To run a workflow with call caching enabled**

The following example demonstrates how to use ``start-run`` with call caching enabled. ::

    aws omics start-run \
        --workflow-id 7206765 \
        --role-arn arn:aws:iam::123456789012:role/HealthOmicsServiceRole \
        --output-uri s3://healthomics-output-bucket-demo/results/ \
        --parameters '{
            "input": "s3://healthomics-output-bucket-demo/input/samplesheet.csv",
            "protocol": "10XV3",
            "ecr_registry": "123456789012.dkr.ecr.us-east-1.amazonaws.com",
            "gtf": "s3://healthomics-output-bucket-demo/reference/genes.gtf",
            "aligner": "star",
            "fasta": "s3://healthomics-output-bucket-demo/reference/genome.fa",
            "skip_emptydrops": "true"
        }' \
        --cache-id 1234567 \
        --cache-behavior "CACHE_ALWAYS"

Output::

    {
        "arn": "arn:aws:omics:us-east-1:123456789012:run/3282892",
        "id": "3282892",
        "status": "PENDING",
        "tags": {},
        "uuid": "b8cbfb50-64f7-359a-443a-24ed14c4d9e8",
        "runOutputUri": "s3://healthomics-output-bucket-demo/results/3282892"
    }

**To duplicate a run**

The following example demonstrates how to use ``start-run`` to duplicate a run with ID ``3282892``. ::

    aws omics start-run \
        --role-arn arn:aws:iam::713632817814:role/HealthOmicsServiceRole \
        --output-uri s3://healthomics-output-bucket-demo/results/ \
        --run-id 3282892

Output::

    {
        "arn": "arn:aws:omics:us-east-1:713632817814:run/6037016",
        "id": "6037016",
        "status": "PENDING",
        "tags": {},
        "uuid": "a0cc0766-def1-cc71-8dc4-1300d3e64f90",
        "runOutputUri": "s3://healthomics-output-bucket-demo/results/6037016"
    }    

For more information, see `Starting a run <https://docs.aws.amazon.com/omics/latest/dev/starting-a-run.html>`__ in the *AWS HealthOmics User Guide*.

**To load source files from AWS HealthOmics**

You can also load source files from AWS HealthOmics storage, by using service-specific URIs. The following example `workflow-inputs.json` file uses AWS HealthOmics URIs for read set and reference genome sources. ::

    {
        "sample_name": "NA12878",
        "input_cram": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/readSet/1234567890/source1",
        "ref_dict": "s3://omics-artifacts-01d6xmpl4e72dd32/Homo_sapiens_assembly38.dict",
        "ref_fasta": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/reference/1234567890",
        "ref_fasta_index": "omics://123456789012.storage.us-west-2.amazonaws.com/1234567890/reference/1234567890/index"
    }

