**To get a thing shadow document**

The following ``get-thing-shadow`` example gets the thing shadow document for the specified IoT thing. ::

    aws iot-data update-thing-shadow \
        --thing-name "RGBLight" \
        file://update.json \
        output.txt

Contents of ``update.json``::

    {
        "state" : {
            "desired" : {
                "color" : "RED"
            },
            "reported" : {
                "color" : "GREEN"
            }
        }
    }

The command produces no output on the display, but the following shows the contents of ``output.txt``::

    {
      "state":{
        "reported":{
        "moisture":"low"
        }
      },
      "metadata":{
        "reported":{
          "moisture":{
            "timestamp":1560269319
          }
        }
      },
      "version":1,"timestamp":1560269405
    }

For more information, see `Device Shadow Service Data Flow <https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-data-flow.html>`__ in the *AWS IoT Developers Guide*.

