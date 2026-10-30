**To update an assessment target**

The following ``update-assessment-target`` example updates the assessment target with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX`` and the name of ``Example``, and the resource group with the ARN of ``arn:aws:inspector:us-west-2:123456789012:resourcegroup/0-yNbgL5Pt``. ::

    aws inspector update-assessment-target \
        --assessment-target-arn arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX \
        --assessment-target-name Example \
        --resource-group-arn arn:aws:inspector:us-west-2:123456789012:resourcegroup/0-yNbgL5Pt

This command produces no output.

