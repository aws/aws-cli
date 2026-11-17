**To create a torrent for an object**

The following ``get-object-torrent`` example creates a torrent for an object in a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-object-torrent large-video-file.torrent \
        --bucket amzn-s3-demo-bucket \
        --key large-video-file.mp4

This command produces no output.

The torrent file is saved locally in the current folder. Note that the output filename (``large-video-file.torrent``) is specified without an option name.

For more information, see `Working with objects in Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/uploading-downloading-objects.html>`__ in the *Amazon S3 User Guide*.
