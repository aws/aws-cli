**To import a model**

The following ``import-model`` example imports a model from a different AWS account. The document classifier model in account ``123456789222`` 
has a resource-based policy allowing account ``123456789111`` to import the model. ::

    aws comprehend import-model \
        --source-model-arn arn:aws:comprehend:us-west-2:123456789222:document-classifier/example-classifier

Output::

    {
        "ModelArn": "arn:aws:comprehend:us-west-2:123456789111:document-classifier/example-classifier"
    }

For more information, see `Copying custom models between AWS accounts <https://docs.aws.amazon.com/comprehend/latest/dg/custom-copy.html>`__ in the *Amazon Comprehend Developer Guide*.