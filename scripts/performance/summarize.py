#!/usr/bin/env python
"""
Summarizes results of benchmarking.

Usage
=====

Run this script with::

    ./summarize performance.csv

The script can also be run with multiple files:

    ./summarize performance.csv performance-2.csv

"""

import argparse
import csv
import json


class Summarizer:
    DATA_INDEX_IN_ROW = {'time': 0, 'memory': 1, 'cpu': 2}

    def __init__(self):
        self.total_files = 0
        self._num_rows = 0
        self._start_time = None
        self._end_time = None
        self._latest_end_time = None
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

    def _average_across_all_files(self, name):
        return sum(self._totals[name]) / len(self._totals[name])

    def _detailed_json_benchmark(
        self, metric_name, description, unit, measurements
    ):
        return {
            'name': metric_name,
            'description': description,
            'unit': unit,
            'date': int(self._latest_end_time),
            'measurements': measurements
        }

    def summarize_as_detailed_json(self):
        """
        Returns detailed JSON summary of processed data, including additional metadata about
        the metrics being measured.

        :return: list of dictionaries with detailed information of a benchmarked metric
        """
        return {
            'results': [
                self._detailed_json_benchmark(
                    metric_name='total_time',
                    description='The total execution time of the command.',
                    unit='Milliseconds',
                    measurements=[total_time * 1000 for total_time in self._totals['time']]
                ),
                self._detailed_json_benchmark(
                    metric_name='max_memory',
                    description='The maximum memory utilization of the CLI throughout execution of the command.',
                    unit='Megabytes',
                    measurements=[max_mem / 1e6 for max_mem in self._totals['max_memory']]
                ),
                self._detailed_json_benchmark(
                    metric_name='average_memory',
                    description='The average memory utilization of the CLI throughout execution of the command.',
                    unit='Megabytes',
                    measurements=[avg_mem / 1e6 for avg_mem in self._totals['average_memory']]
                ),
                self._detailed_json_benchmark(
                    metric_name='max_cpu_utilization',
                    description='The maximum CPU utilization of the CLI throughout execution of the command.',
                    unit='Percentage',
                    measurements=[max_cpu for max_cpu in self._totals['max_cpu']]
                ),
                self._detailed_json_benchmark(
                    metric_name='average_cpu_utilization',
                    description='The average CPU utilization of the CLI throughout execution of the command.',
                    unit='Percentage',
                    measurements=[avg_cpu for avg_cpu in self._totals['average_cpu']]
                ),
            ]
        }

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

            # Keep track of the latest end time across all files
            if self._latest_end_time is None or self._latest_end_time < self._end_time:
                self._latest_end_time = self._end_time

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
            'more than one of these files, it will aggregate the measurements '
            'from each into a single output.'
        ),
    )
    args = parser.parse_args()
    summarizer = Summarizer()
    summarizer.process(args)
    result = json.dumps(summarizer.summarize_as_detailed_json(), indent=2)
    print(result)


if __name__ == '__main__':
    main()
