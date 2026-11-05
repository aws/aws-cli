**To start an assessment run**

The following ``start-assessment-run`` example starts the assessment run named ``examplerun`` using the assessment template with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-it5r2S4T``. ::

    aws inspector start-assessment-run \
        --assessment-run-name examplerun \
        --assessment-template-arn arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-it5r2S4T

Output::

    {
        "assessmentRunArn": "arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-it5r2S4T/run/0-jOoroxyY"
    }

