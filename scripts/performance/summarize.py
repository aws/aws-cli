#!/usr/bin/env python
"""
Summarizes results of benchmarking.

Usage
=====

Run this script with::

    ./summarize performance.csv


And that should output::

    +------------------------+----------+----------------------+
    | Metric over 1 run(s)   | Mean     | Standard Deviation   |
    +========================+==========+======================+
    | Total Time (seconds)   | 1.200    | 0.0                  |
    +------------------------+----------+----------------------+
    | Maximum Memory         | 42.3 MiB | 0 Bytes              |
    +------------------------+----------+----------------------+
    | Maximum CPU (percent)  | 88.1     | 0.0                  |
    +------------------------+----------+----------------------+
    | Average Memory         | 33.9 MiB | 0 Bytes              |
    +------------------------+----------+----------------------+
    | Average CPU (percent)  | 30.5     | 0.0                  |
    +------------------------+----------+----------------------+


The script can also be ran with multiple files:

    ./summarize performance.csv performance-2.csv

And will have a similar output:

    +------------------------+----------+----------------------+
    | Metric over 2 run(s)   | Mean     | Standard Deviation   |
    +========================+==========+======================+
    | Total Time (seconds)   | 1.155    | 0.0449999570847      |
    +------------------------+----------+----------------------+
    | Maximum Memory         | 42.5 MiB | 110.0 KiB            |
    +------------------------+----------+----------------------+
    | Maximum CPU (percent)  | 94.5     | 6.45                 |
    +------------------------+----------+----------------------+
    | Average Memory         | 35.6 MiB | 1.7 MiB              |
    +------------------------+----------+----------------------+
    | Average CPU (percent)  | 27.5     | 3.03068181818        |
    +------------------------+----------+----------------------+


You can also specify the ``--output-format json`` option to print the
summary as JSON instead of a pretty printed table::

    {
      "total_time": 72.76999998092651,
      "std_dev_average_memory": 0.0,
      "std_dev_total_time": 0.0,
      "average_memory": 56884518.57534247,
      "std_dev_average_cpu": 0.0,
      "std_dev_max_memory": 0.0,
      "average_cpu": 61.19315068493151,
      "max_memory": 58331136.0
    }

"""

import argparse
import csv
import json
from math import sqrt

from tabulate import tabulate


def human_readable_size(value):
    """Converts integer values in bytes to human readable values"""
    hummanize_suffixes = ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    base = 1024
    bytes_int = float(value)

    if bytes_int == 1:
        return '1 Byte'
    elif bytes_int < base:
        return '%d Bytes' % bytes_int

    for i, suffix in enumerate(hummanize_suffixes):
        unit = base ** (i + 2)
        if round((bytes_int / unit) * base) < base:
            return f'{(base * bytes_int / unit):.1f} {suffix}'


class Summarizer:
    DATA_INDEX_IN_ROW = {'time': 0, 'memory': 1, 'cpu': 2}

    def __init__(self):
        self.total_files = 0
        self._num_rows = 0
        self._start_time = None
        self._end_time = None
        self._totals = {
            'time': [],
            'average_memory': [],
            'average_cpu': [],
            'max_memory': [],
            'max_cpu': [],
        }
        self._averages = {
            'memory': 0.0,
            'cpu': 0.0,
        }
        self._maximums = {'memory': 0.0, 'cpu': 0.0}

    @property
    def total_time(self):
        return self._average_across_all_files('time')

    @property
    def max_cpu(self):
        return self._average_across_all_files('max_cpu')

    @property
    def max_memory(self):
        return self._average_across_all_files('max_memory')

    @property
    def average_cpu(self):
        return self._average_across_all_files('average_cpu')

    @property
    def average_memory(self):
        return self._average_across_all_files('average_memory')

    @property
    def std_dev_total_time(self):
        return self._standard_deviation_across_all_files('time')

    @property
    def std_dev_max_cpu(self):
        return self._standard_deviation_across_all_files('max_cpu')

    @property
    def std_dev_max_memory(self):
        return self._standard_deviation_across_all_files('max_memory')

    @property
    def std_dev_average_cpu(self):
        return self._standard_deviation_across_all_files('average_cpu')

    @property
    def std_dev_average_memory(self):
        return self._standard_deviation_across_all_files('average_memory')

    def _average_across_all_files(self, name):
        return sum(self._totals[name]) / len(self._totals[name])

    def _standard_deviation_across_all_files(self, name):
        mean = self._average_across_all_files(name)
        differences = [total - mean for total in self._totals[name]]
        sq_differences = [difference**2 for difference in differences]
        return sqrt(sum(sq_differences) / len(self._totals[name]))

    def summarize_as_table(self):
        """Formats the processed data as pretty printed table.

        :return: str of formatted table
        """
        h = human_readable_size
        table = [
            [
                'Total Time (seconds)',
                f'{self.total_time:.3f}',
                self.std_dev_total_time,
            ],
            ['Maximum Memory', h(self.max_memory), h(self.std_dev_max_memory)],
            [
                'Maximum CPU (percent)',
                f'{self.max_cpu:.1f}',
                self.std_dev_max_cpu,
            ],
            [
                'Average Memory',
                h(self.average_memory),
                h(self.std_dev_average_memory),
            ],
            [
                'Average CPU (percent)',
                f'{self.average_cpu:.1f}',
                self.std_dev_average_cpu,
            ],
        ]
        return tabulate(
            table,
            headers=[
                f'Metric over {self.total_files} run(s)',
                'Mean',
                'Standard Deviation',
            ],
            tablefmt="grid",
        )

    def summarize_as_json(self):
        """Return JSON summary of processed data.

        :return: str of formatted JSON
        """
        return json.dumps(
            {
                'total_time': self.total_time,
                'std_dev_total_time': self.std_dev_total_time,
                'max_memory': self.max_memory,
                'std_dev_max_memory': self.std_dev_max_memory,
                'average_memory': self.average_memory,
                'std_dev_average_memory': self.std_dev_average_memory,
                'average_cpu': self.average_cpu,
                'std_dev_average_cpu': self.std_dev_average_cpu,
            },
            indent=2,
        )

    def process(self, args):
        """Processes the data from the CSV file"""
        for benchmark_file in args.benchmark_files:
            self.process_individual_file(benchmark_file)
            self.total_files += 1

    def process_individual_file(self, benchmark_file):
        with open(benchmark_file) as f:
            reader = csv.reader(f)
            # Process each row from the CSV file
            row = None
            for row in reader:
                self._validate_row(row, benchmark_file)
                self.process_data_row(row)
            self._validate_row(row, benchmark_file)
            self._end_time = self._get_time(row)
            self._finalize_processed_data_for_file()

    def _validate_row(self, row, filename):
        if not row:
            raise RuntimeError(
                f'Row: {row} could not be processed. The CSV file ({filename}) may be '
                'empty.'
            )

    def process_data_row(self, row):
        # If the row is the first row collect the start time.
        if self._num_rows == 0:
            self._start_time = self._get_time(row)
        self._num_rows += 1
        self.process_data_point(row, 'memory')
        self.process_data_point(row, 'cpu')

    def process_data_point(self, row, name):
        # Determine where in the CSV row the requested data is located.
        index = self.DATA_INDEX_IN_ROW[name]
        # Get the data point.
        data_point = float(row[index])
        self._add_to_average(name, data_point)
        self._account_for_maximum(name, data_point)

    def _finalize_processed_data_for_file(self):
        # Add numbers to the total, which keeps track of data over
        # all files provided.
        self._totals['time'].append(self._end_time - self._start_time)
        self._totals['max_cpu'].append(self._maximums['cpu'])
        self._totals['max_memory'].append(self._maximums['memory'])
        self._totals['average_cpu'].append(
            self._averages['cpu'] / self._num_rows
        )
        self._totals['average_memory'].append(
            self._averages['memory'] / self._num_rows
        )

        # Reset some of the data needed to be tracked for each specific
        # file.
        self._num_rows = 0
        self._maximums = self._maximums.fromkeys(self._maximums, 0.0)
        self._averages = self._averages.fromkeys(self._averages, 0.0)

    def _get_time(self, row):
        return float(row[self.DATA_INDEX_IN_ROW['time']])

    def _add_to_average(self, name, data_point):
        self._averages[name] += data_point

    def _account_for_maximum(self, name, data_point):
        if data_point > self._maximums[name]:
            self._maximums[name] = data_point


def main():
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument(
        'benchmark_files',
        nargs='+',
        help=(
            'The CSV output file from the benchmark script. If you provide'
            'more than one of these files, it will give you the average '
            'across all of the files for each metric.'
        ),
    )
    parser.add_argument(
        '-f',
        '--output-format',
        default='table',
        choices=['table', 'json'],
        help=(
            'Specify what output format to use for displaying results. '
            'By default, a pretty printed table is used, but you can also '
            'specify "json" to display pretty printed JSON.'
        ),
    )
    args = parser.parse_args()
    summarizer = Summarizer()
    summarizer.process(args)
    if args.output_format == 'table':
        result = summarizer.summarize_as_table()
    else:
        result = summarizer.summarize_as_json()
    print(result)


if __name__ == '__main__':
    main()
