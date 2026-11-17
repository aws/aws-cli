**To set tags for a resource**

The following ``set-tags-for-resource`` example sets the tag with the key of ``Example`` and value of ``example`` to the assessment template with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-7sbz2Kz0``. ::

    aws inspector set-tags-for-resource \
        --resource-arn arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-7sbz2Kz0 \
        --tags key=Example,value=example

This command produces no output.

