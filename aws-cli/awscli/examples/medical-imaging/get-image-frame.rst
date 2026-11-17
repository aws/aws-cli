**To get image set pixel data**

The following ``get-image-frame`` example gets an image frame. ::

    aws medical-imaging get-image-frame imageframe.jph \
        --datastore-id "12345678901234567890123456789012" \
        --image-set-id "98765412345612345678907890789012" \
        --image-frame-information imageFrameId=3abf5d5d7ae72f80a0ec81b2c0de3ef4

Output::

    {
        "contentType": "application/octet-stream"
    }

The ``GetImageFrame`` action writes the stream of pixel data to the ``imageframe.jph`` file. For information about decoding and viewing image frames, see HTJ2K decoding libraries.

For more information, see `Getting image set pixel data <https://docs.aws.amazon.com/healthimaging/latest/devguide/get-image-frame.html>`__ in the *AWS HealthImaging Developer Guide*.
