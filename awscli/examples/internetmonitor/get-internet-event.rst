**To describe an event reported by an internet monitor**

This example uses the ``get-internet-event`` command to describe the details reported by a specific event in an internet monitor. ::

    aws internetmonitor get-internet-event \
        --event-id ba755fe8-b4de-4e24-8b3b-19267bec227e

Output::

    {
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
    }