import json
import os

responses = [
    {
        "headers": {"Content-Length": "10000000000", "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT", "ETag": "etag-1"}
    }
]

PART_SIZE = 8388608
OBJECT_SIZE = 10000000000
# TOTAL_PARTS = 1192

cursor = 0
for i in range(31):
    responses.append({
        "headers": {
            "Content-Length": "8388608",
            "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT",
            "ETag": "etag-1",
            "Accept-Ranges": "bytes",
            "Content-Range": f'{cursor}-{cursor+PART_SIZE}/{OBJECT_SIZE}'
        },
        "body": {
          "file": "standard_part"
        }
      })
    cursor += PART_SIZE

# 1161 left
# simulate incomplete read
# responses.append({
#         "headers": {
#             "Content-Length": "8388608",
#             "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT",
#             "ETag": "etag-1",
#             "Accept-Ranges": "bytes",
#             "Content-Range": f'{cursor}-{cursor+PART_SIZE}/{OBJECT_SIZE}'
#         },
#         "body": {
#           "file": "last_part"
#         }
#       })

# retry of incomplete chunk
responses.append({
        "headers": {
            "Content-Length": "8388608",
            "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT",
            "ETag": "etag-1",
            "Accept-Ranges": "bytes",
            "Content-Range": f'{cursor}-{cursor+PART_SIZE}/{OBJECT_SIZE}'
        },
        "body": {
          "file": "standard_part"
        }
      })

cursor += PART_SIZE
# 1160 left

# rest of the "full" parts
for i in range(1160):
    responses.append({
        "headers": {
            "Content-Length": "8388608",
            "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT",
            "ETag": "etag-1",
            "Accept-Ranges": "bytes",
            "Content-Range": f'{cursor}-{cursor+PART_SIZE}/{OBJECT_SIZE}'
        },
        "body": {
          "file": "standard_part"
        }
      })
    cursor += PART_SIZE

# last part
responses.append({
        "headers": {
            "Content-Length": "779264",
            "Last-Modified": "Thu, 18 Oct 2018 23:00:00 GMT",
            "ETag": "etag-1",
            "Accept-Ranges": "bytes",
            "Content-Range": f'{cursor}-{cursor+779264}/{OBJECT_SIZE}'
        },
        "body": {
          "file": "last_part"
        }
      })

responses.append({})

out_path = os.path.join(os.path.abspath('out2.successful.json'))
with open(out_path, 'w') as f:
    f.write(json.dumps(responses))
    f.flush()