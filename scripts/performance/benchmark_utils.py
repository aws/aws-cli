import csv
import math

import s3transfer
import os
import subprocess
import uuid
import shutil
import argparse
import tempfile


class Summarizer:
    DATA_INDEX_IN_ROW = {'time': 0, 'memory': 1, 'cpu': 2}

    def __init__(self):
        self._num_rows = 0
        self._start_time = None
        self._end_time = None
        self._averages = {
            'memory': 0.0,
            'cpu': 0.0,
        }
        self._samples = {
            'memory': [],
            'cpu': [],
        }
        self._maximums = {'memory': 0.0, 'cpu': 0.0}

    def summarize(self, benchmark_file):
        """Processes the data from the CSV file"""
        with open(benchmark_file) as f:
            reader = csv.reader(f)
            # Process each row from the CSV file
            row = None
            for row in reader:
                self._validate_row(row, benchmark_file)
                self.process_data_row(row)
            self._validate_row(row, benchmark_file)
            self._end_time = self._get_time(row)
            metrics = self._finalize_processed_data_for_file()
        return metrics

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
        self._samples[name].append(data_point)

    def _finalize_processed_data_for_file(self):
        self._samples['memory'].sort()
        self._samples['cpu'].sort()
        metrics = {
            'time': self._end_time - self._start_time,
            'average_memory': self._averages['memory'] / self._num_rows,
            'average_cpu': self._averages['cpu'] / self._num_rows,
            'max_memory': self._maximums['memory'],
            'max_cpu': self._maximums['cpu'],
            'memory_p50': self._compute_metric_percentile(50, 'memory'),
            'memory_p95': self._compute_metric_percentile(95, 'memory'),
            'cpu_p50': self._compute_metric_percentile(50, 'cpu'),
            'cpu_p95': self._compute_metric_percentile(95, 'cpu'),
        }
        # Reset some of the data needed to be tracked for each execution
        self._num_rows = 0
        self._maximums = self._maximums.fromkeys(self._maximums, 0.0)
        self._averages = self._averages.fromkeys(self._averages, 0.0)
        self._samples['memory'].clear()
        self._samples['cpu'].clear()
        return metrics

    def _compute_metric_percentile(self, percentile, name):
        num_samples = len(self._samples[name])
        p_idx = math.ceil(percentile*num_samples/100) - 1
        return self._samples[name][p_idx]

    def _get_time(self, row):
        return float(row[self.DATA_INDEX_IN_ROW['time']])

    def _add_to_average(self, name, data_point):
        self._averages[name] += data_point

    def _account_for_maximum(self, name, data_point):
        if data_point > self._maximums[name]:
            self._maximums[name] = data_point
