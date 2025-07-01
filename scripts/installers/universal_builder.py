#!/usr/bin/env python3
"""Helper module for building universal Mac binaries."""

import os
import subprocess
import logging
import shutil
from glob import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UniversalBuilder:
    def __init__(self, python_path='/Library/Frameworks/Python.framework/Versions/Current/bin/python3'):
        self.python_path = python_path
        self.native_extensions = [
            '_awscrt*.so',
            '_ruamel_yaml*.so',
        ]

    def setup_venv(self, venv_path: str, arch: str) -> None:
        logger.info(f"Creating {arch} venv at {venv_path}")
        subprocess.run([self.python_path, '-m', 'venv', venv_path], check=True)
        pip_cmd = f"""
            source {venv_path}/bin/activate
            pip install --upgrade pip setuptools wheel
            ARCHFLAGS="-arch {arch}" pip install --no-binary :all: awscrt ruamel.yaml.clib
        """
        cmd = ['arch', '-x86_64', 'bash', '-c', pip_cmd] if arch == 'x86_64' else ['bash', '-c', pip_cmd]
        subprocess.run(cmd, check=True)

    def _get_site_packages(self, venv_path: str) -> str:
        output = subprocess.check_output(
            f"source {venv_path}/bin/activate && python -c 'import site; print(site.getsitepackages()[0])'",
            shell=True, text=True, executable="/bin/bash"
        )
        return output.strip()

    def merge_binaries(self, arm_venv: str, x86_venv: str, output_dir: str) -> None:
        logger.info("Merging native extensions into universal binaries")
        os.makedirs(output_dir, exist_ok=True)
        arm_site = self._get_site_packages(arm_venv)
        x86_site = self._get_site_packages(x86_venv)
        for pattern in self.native_extensions:
            arm_paths = glob(os.path.join(arm_site, pattern))
            x86_paths = glob(os.path.join(x86_site, pattern))
            if not arm_paths or not x86_paths:
                raise FileNotFoundError(f"Could not find '{pattern}' in both envs")
            output_path = os.path.join(output_dir, os.path.basename(arm_paths[0]))
            subprocess.run(['lipo', '-create', arm_paths[0], x86_paths[0], '-output', output_path], check=True)

    def copy_to(self, src_dir: str, dest_dir: str) -> None:
        os.makedirs(dest_dir, exist_ok=True)
        for so_file in glob(os.path.join(src_dir, '*.so')):
            shutil.copy2(so_file, os.path.join(dest_dir, os.path.basename(so_file)))

    def verify_universal_binary(self, binary_path: str) -> bool:
        result = subprocess.run(['lipo', '-info', binary_path], capture_output=True, text=True)
        return all(arch in result.stdout for arch in ['x86_64', 'arm64'])