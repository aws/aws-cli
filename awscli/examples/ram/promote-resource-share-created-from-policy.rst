**To promote a resource-policy based resource share to full functionality in AWS RAM**

The following ``promote-resource-share-created-from-policy`` example takes a resource share that you created implicitly by attaching a resource-based policy, and converts it to be fully functional with the AWS RAM console and its CLI and API operations. ::

    aws ram promote-resource-share-created-from-policy \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "returnValue": true
    }

For more information, see `What about cross-account access with resource-based policies? <https://docs.aws.amazon.com/ram/latest/userguide/what-is.html#what-is-about-res-pol-sharing>`__ in the *AWS RAM User Guide*.
