**To list the events reported by an internet monitor**

This example uses the ``list-internet-events`` command to return all the events reported by an internet monitor. ::

    aws internetmonitor list-internet-events

Output::

    {
        "InternetEvents": [{
            "EventId": "ba755fe8-b4de-4e24-8b3b-19267bec227e",
            "EventArn": "arn:aws:internetmonitor::123456789012:internet-event/ba755fe8-b4de-4e24-8b3b-19267bec227e",
            "StartedAt": "2024-08-27T21:04:00+00:00",
            "EndedAt": "2024-08-28T03:30:00+00:00",
            "ClientLocation": {
                "ASName": "CHARTER-20115",
                "ASNumber": 20115,
                "Country": "United States",
                "Subdivision": "Michigan",
                "Metro": "505",
                "City": "Fenton",
                "Latitude": 42.7893,
                "Longitude": -83.7135
            },
            "EventType": "AVAILABILITY",
            "EventStatus": "RESOLVED"
        }]
    }