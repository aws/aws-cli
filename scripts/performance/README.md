# AWS CLI Performance Benchmarks

This document outlines details of the AWS CLI performance benchmarks,
including how to run benchmarks and how to add your own.

## Running the Benchmarks

Our benchmark executor works by running all benchmarks defined in
`benchmarks.json`. For each benchmark defined in this JSON file, it
runs the command for a configurable number of iterations (default: 1)
and benchmarks metrics such as memory usage, CPU utilization, and
timings.

The benchmark executor also stubs an HTTP client with mock responses
defined in `benchmarks.json`. This ensures the timings produced in
the results reflect only the AWS CLI and **not** external factors
such as service latency or network throughput.

### Example

The following example command runs the benchmarks defined in `benchmarks.json`,
and executes each command 2 times.

`./run-benchmarks --num-iterations 2`

An example output for this command is shown below.

```json
{
   "results":[
      {
         "name":"s3.cp.upload",
         "dimensions":[
            {
               "FileSize":"32MB"
            },
            {
               "S3TransferClient":"Classic"
            }
         ],
         "measurements":[
            {
               "total_time":0.2531106472015381,
               "max_memory":76791808.0,
               "max_cpu":5.0,
               "p50_memory":51412992.0,
               "p95_memory":75235328.0,
               "p50_cpu":1.5,
               "p95_cpu":2.4,
               "first_client_invocation_time":0.24789667129516602
            },
            {
               "total_time":0.17595314979553223,
               "max_memory":76939264.0,
               "max_cpu":6.2,
               "p50_memory":52297728.0,
               "p95_memory":75710464.0,
               "p50_cpu":2.1,
               "p95_cpu":2.5,
               "first_client_invocation_time":0.17173004150390625
            }
         ]
      },
      {
         "name":"s3.cp.upload",
         "dimensions":[
            {
               "FileSize":"32MB"
            },
            {
               "S3TransferClient":"CRT"
            }
         ],
         "measurements":[
            {
               "total_time":0.7724411487579346,
               "max_memory":81002496.0,
               "max_cpu":4.1,
               "p50_memory":78479360.0,
               "p95_memory":80822272.0,
               "p50_cpu":0.0,
               "p95_cpu":2.4,
               "first_client_invocation_time":0.17360806465148926
            },
            {
               "total_time":0.6735439300537109,
               "max_memory":80658432.0,
               "max_cpu":5.2,
               "p50_memory":78495744.0,
               "p95_memory":80412672.0,
               "p50_cpu":0.0,
               "p95_cpu":2.4,
               "first_client_invocation_time":0.17362713813781738
            }
         ]
      },
      {
         "name":"s3.mv.upload",
         "dimensions":[
            {
               "FileSize":"32MB"
            }
         ],
         "measurements":[
            {
               "total_time":0.17440271377563477,
               "max_memory":76972032.0,
               "max_cpu":4.6,
               "p50_memory":52166656.0,
               "p95_memory":75776000.0,
               "p50_cpu":2.1,
               "p95_cpu":2.5,
               "first_client_invocation_time":0.16981887817382812
            },
            {
               "total_time":0.17231082916259766,
               "max_memory":75825152.0,
               "max_cpu":6.1,
               "p50_memory":52199424.0,
               "p95_memory":74842112.0,
               "p50_cpu":2.1,
               "p95_cpu":2.5,
               "first_client_invocation_time":0.16803598403930664
            }
         ]
      },
      {
         "name":"s3.mv.download",
         "dimensions":[
            {
               "FileSize":"32MB"
            },
            {
               "S3TransferClient":"Classic"
            }
         ],
         "measurements":[
            {
               "total_time":0.17304229736328125,
               "max_memory":76152832.0,
               "max_cpu":4.0,
               "p50_memory":52674560.0,
               "p95_memory":74907648.0,
               "p50_cpu":2.1,
               "p95_cpu":2.4,
               "first_client_invocation_time":0.16739511489868164
            },
            {
               "total_time":0.16962409019470215,
               "max_memory":76693504.0,
               "max_cpu":4.9,
               "p50_memory":52314112.0,
               "p95_memory":75431936.0,
               "p50_cpu":2.1,
               "p95_cpu":2.6,
               "first_client_invocation_time":0.16400408744812012
            }
         ]
      },
      {
         "name":"s3.sync.upload",
         "dimensions":[
            {
               "FileCount":"5,000"
            },
            {
               "FileSize":"4KB"
            },
            {
               "S3TransferClient":"Classic"
            }
         ],
         "measurements":[
            {
               "total_time":11.370934963226318,
               "max_memory":134578176.0,
               "max_cpu":20.7,
               "p50_memory":106397696.0,
               "p95_memory":132235264.0,
               "p50_cpu":2.4,
               "p95_cpu":2.7,
               "first_client_invocation_time":0.6362888813018799
            },
            {
               "total_time":12.029011964797974,
               "max_memory":134676480.0,
               "max_cpu":18.6,
               "p50_memory":105955328.0,
               "p95_memory":131727360.0,
               "p50_cpu":2.4,
               "p95_cpu":2.7,
               "first_client_invocation_time":0.6395571231842041
            }
         ]
      },
      {
         "name":"s3.sync.upload",
         "dimensions":[
            {
               "FileCount":"5,000"
            },
            {
               "FileSize":"4KB"
            },
            {
               "S3TransferClient":"CRT"
            }
         ],
         "measurements":[
            {
               "total_time":90.28388690948486,
               "max_memory":188809216.0,
               "max_cpu":17.9,
               "p50_memory":144375808.0,
               "p95_memory":188792832.0,
               "p50_cpu":0.0,
               "p95_cpu":3.4,
               "first_client_invocation_time":0.656865119934082
            },
            {
               "total_time":84.99997591972351,
               "max_memory":190808064.0,
               "max_cpu":20.7,
               "p50_memory":143917056.0,
               "p95_memory":186728448.0,
               "p50_cpu":0.0,
               "p95_cpu":3.5,
               "first_client_invocation_time":0.7549021244049072
            }
         ]
      }
   ]
}
```

## Defining Your own Benchmarks for Local Performance Testing

To create your own benchmark definitions, create a file on your machine containing
a JSON-formatted list of benchmark definitions. Each benchmark definition supports
the keys below. Each key is required unless specified otherwise.

- `name` (string): The name of the benchmark.
- `command` (list): The AWS CLI command to benchmark, including arguments.
    - Each element of the list is a string component of the command.
    - Example value: `["s3", "cp", "test_file", "s3://bucket/test_file", "--quiet"]`.
- `dimensions` (list) **(optional)**: Used to specify additional dimensions for
interpreting this metric.
  - Each element in the list is an object with the following keys:
    - `name` (string): Name of the dimensions
    - `value` (string): Value of the dimension
- `environment` (object) **(optional)**: Specifies settings for the environment to run
the command in.
  - The environment object supports the following keys:
    - `file_literals` (list) **(optional)**: Specifies files that must be
created before executing the benchmark. The files created will contain
the specified contents.
      - Each element is an object with the following keys:
        - `name` (string): Name of the file to create
        - `content` (string): The contents of the file.
        - `mode` (string) **(optional)**: The write mode to use for writing the
file contents.
          - Default: `w`
    - `files` (list) **(optional)**: Specifies the files that must be
created before executing the benchmark. The files created will be filled with
null bytes to achieve the specified size.
      - Each element is an object with the following keys:
        - `name` (string): Name of the file to create
        - `size` (int): The size of the file to create in bytes.
    - `file_dirs` (list) **(optional)**: Specifies the directories that must
be created before executing the benchmark. The directories will be created
and filled with the specified number of files, each of which will be filled
with null bytes to achieve the specified file size.
      - Each element is an object with the following keys:
        - `name` (string): Name of the directory
        - `file_count` (int): The number of files to create in the directory.
        - `file_size` (int): The size of each file in the directory, in bytes.
    - `config` (string) **(optional)**: The contents of the AWS config
file to use for the benchmark execution.
      - Default: `"[default]"`.
      - Example value: `"[default]\ns3 =\n preferred_transfer_client = crt"`
- `responses` (list) **(optional)**: A list of HTTP responses to stub from
the service for each request made during command execution.
  - Default: `[{{"headers": {}, "body": ""}]`
  - Each element of the list is an object with the following keys:
    - `status_code` (int) **(optional)**: The status code of the response.
      - Default: `200`
    - `headers` (object) **(optional)**: Used to specify the HTTP headers of
the response. Each key-value pair corresponds to a single header name (key)
and its value.
      - Default: `{}`
    - `body` (string | object) **(optional)**: The raw HTTP response body.
      - Default: `""`
      - If body is an object, it supports the following keys:
        - `file` (string): The name of a file whose contents will be used as
the response body. This can refer to files created under the `environment`
definition.
    - `instances` (int) **(optional)**: The total number of times to stub
this response; this prevents the need to repeat the same response many times.
      - Default: 1
      - This is useful for commands such as `aws s3 sync`, that may execute many
      HTTP requests with similar responses.
