# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Display strategy implementations for ECS Express Gateway Service monitoring."""

import asyncio
import time

from botocore.exceptions import ClientError

from awscli.customizations.utils import uni_print


class DisplayStrategy:
    """Base class for display strategies.

    Each strategy controls its own execution model, timing, and output format.
    """

    def execute(self, collector, start_time, timeout_minutes):
        """Execute the monitoring loop.

        Args:
            collector: ServiceViewCollector instance for data fetching
            start_time: Start timestamp for timeout calculation
            timeout_minutes: Maximum monitoring duration in minutes
        """
        raise NotImplementedError


class InteractiveDisplayStrategy(DisplayStrategy):
    """Interactive display strategy with async spinner and keyboard navigation.

    Uses dual async tasks:
    - Data task: Polls ECS APIs every 5 seconds
    - Spinner task: Updates display every 100ms with rotating spinner
    """

    def __init__(self, display, use_color):
        self.display = display
        self.use_color = use_color

    def execute(self, collector, start_time, timeout_minutes):
        """Execute async monitoring with spinner and keyboard controls."""
        final_output, timed_out = asyncio.run(
            self._execute_async(collector, start_time, timeout_minutes)
        )
        if timed_out:
            uni_print(final_output + "\nMonitoring timed out!\n")
        else:
            uni_print(final_output + "\nMonitoring Complete!\n")

    async def _execute_async(self, collector, start_time, timeout_minutes):
        """Async execution with dual tasks for data and spinner."""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spinner_index = 0
        current_output = "Waiting for initial data"
        timed_out = False

        async def update_data():
            nonlocal current_output, timed_out
            while True:
                current_time = time.time()
                if current_time - start_time > timeout_minutes * 60:
                    timed_out = True
                    self.display.app.exit()
                    break

                try:
                    loop = asyncio.get_event_loop()
                    new_output = await loop.run_in_executor(
                        None, collector.get_current_view, "{SPINNER}"
                    )
                    current_output = new_output
                except ClientError as e:
                    if (
                        e.response.get('Error', {}).get('Code')
                        == 'InvalidParameterException'
                    ):
                        error_message = e.response.get('Error', {}).get(
                            'Message', ''
                        )
                        if (
                            "Cannot call DescribeServiceRevisions for a service that is INACTIVE"
                            in error_message
                        ):
                            current_output = "Service is inactive"
                        else:
                            raise
                    else:
                        raise

                await asyncio.sleep(5.0)

        async def update_spinner():
            nonlocal spinner_index
            while True:
                spinner_char = spinner_chars[spinner_index]
                display_output = current_output.replace(
                    "{SPINNER}", spinner_char
                )
                status_text = f"Getting updates... {spinner_char} | up/down to scroll, q to quit"
                self.display.display(display_output, status_text)
                spinner_index = (spinner_index + 1) % len(spinner_chars)
                await asyncio.sleep(0.1)

        data_task = asyncio.create_task(update_data())
        spinner_task = asyncio.create_task(update_spinner())
        display_task = None

        try:
            display_task = asyncio.create_task(self.display.run())

            done, pending = await asyncio.wait(
                [display_task, data_task], return_when=asyncio.FIRST_COMPLETED
            )

            if data_task in done:
                # Await to retrieve result or re-raise any exception from the
                # task. asyncio.wait() doesn't retrieve exceptions itself.
                await data_task

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                # Await cancelled task to ensure proper cleanup and prevent
                # warnings about unawaited tasks
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        finally:
            spinner_task.cancel()
            if display_task is not None and not display_task.done():
                display_task.cancel()
                # Await cancelled task to ensure proper cleanup and prevent
                # warnings about unawaited tasks
                try:
                    await display_task
                except asyncio.CancelledError:
                    pass

        return current_output.replace("{SPINNER}", ""), timed_out
