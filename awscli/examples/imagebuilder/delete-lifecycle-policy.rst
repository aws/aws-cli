**To delete a lifecycle policy**

The following ``delete-lifecycle-policy`` example deletes the specified lifecycle policy. ::

    aws imagebuilder delete-lifecycle-policy \
        --lifecycle-policy-arn arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy

Output::

    {
        "lifecyclePolicyArn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy"
    }

For more information, see `Manage lifecycle policies for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-image-lifecycles.html>`__ in the *EC2 Image Builder User Guide*.
