# ------------------------------------------------------------------
# Copyright (c) 2024 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_entry_point

# All known `opentelementry_` entry-point groups
ENTRY_POINT_GROUPS = (
    'opentelemetry_context',
    'opentelemetry_environment_variables',
    'opentelemetry_id_generator',
    'opentelemetry_logger_provider',
    'opentelemetry_logs_exporter',
    'opentelemetry_meter_provider',
    'opentelemetry_metrics_exporter',
    'opentelemetry_propagator',
    'opentelemetry_resource_detector',
    'opentelemetry_tracer_provider',
    'opentelemetry_traces_exporter',
    'opentelemetry_traces_sampler',
)

# Collect entry points
datas = set()
hiddenimports = set()

for entry_point_group in ENTRY_POINT_GROUPS:
    ep_datas, ep_hiddenimports = collect_entry_point(entry_point_group)
    datas.update(ep_datas)
    hiddenimports.update(ep_hiddenimports)

datas = list(datas)
hiddenimports = list(hiddenimports)
