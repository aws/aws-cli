**To enable block public access for AMIs in the current Region**

The following ``enable-image-block-public-access`` example enables block public access for AMIs at the account level in the current Region. ::

    aws ec2 enable-image-block-public-access \
        --image-block-public-access-state block-new-sharing

Output::

    {
        "ImageBlockPublicAccessState": "block-new-sharing"
    }

For more information, see `Block public access to your AMIs <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-public-access-to-amis.html>`__ in the *Amazon EC2 User Guide*.
