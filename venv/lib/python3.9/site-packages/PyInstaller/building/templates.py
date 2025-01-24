#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Templates to generate .spec files.
"""

onefiletmplt = """# -*- mode: python ; coding: utf-8 -*-
%(preamble)s
%(cipher_init)s

a = Analysis(
    %(scripts)s,
    pathex=%(pathex)s,
    binaries=%(binaries)s,
    datas=%(datas)s,
    hiddenimports=%(hiddenimports)s,
    hookspath=%(hookspath)r,
    hooksconfig={},
    runtime_hooks=%(runtime_hooks)r,
    excludes=%(excludes)s,
    win_no_prefer_redirects=%(win_no_prefer_redirects)s,
    win_private_assemblies=%(win_private_assemblies)s,
    cipher=block_cipher,
    noarchive=%(noarchive)s,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
%(splash_init)s
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,%(splash_target)s%(splash_binaries)s
    %(options)s,
    name='%(name)s',
    debug=%(debug_bootloader)s,
    bootloader_ignore_signals=%(bootloader_ignore_signals)s,
    strip=%(strip)s,
    upx=%(upx)s,
    upx_exclude=%(upx_exclude)s,
    runtime_tmpdir=%(runtime_tmpdir)r,
    console=%(console)s,
    disable_windowed_traceback=%(disable_windowed_traceback)s,
    argv_emulation=%(argv_emulation)r,
    target_arch=%(target_arch)r,
    codesign_identity=%(codesign_identity)r,
    entitlements_file=%(entitlements_file)r,%(exe_options)s
)
"""

onedirtmplt = """# -*- mode: python ; coding: utf-8 -*-
%(preamble)s
%(cipher_init)s

a = Analysis(
    %(scripts)s,
    pathex=%(pathex)s,
    binaries=%(binaries)s,
    datas=%(datas)s,
    hiddenimports=%(hiddenimports)s,
    hookspath=%(hookspath)r,
    hooksconfig={},
    runtime_hooks=%(runtime_hooks)r,
    excludes=%(excludes)s,
    win_no_prefer_redirects=%(win_no_prefer_redirects)s,
    win_private_assemblies=%(win_private_assemblies)s,
    cipher=block_cipher,
    noarchive=%(noarchive)s,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
%(splash_init)s
exe = EXE(
    pyz,
    a.scripts,%(splash_target)s
    %(options)s,
    exclude_binaries=True,
    name='%(name)s',
    debug=%(debug_bootloader)s,
    bootloader_ignore_signals=%(bootloader_ignore_signals)s,
    strip=%(strip)s,
    upx=%(upx)s,
    console=%(console)s,
    disable_windowed_traceback=%(disable_windowed_traceback)s,
    argv_emulation=%(argv_emulation)r,
    target_arch=%(target_arch)r,
    codesign_identity=%(codesign_identity)r,
    entitlements_file=%(entitlements_file)r,%(exe_options)s
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,%(splash_binaries)s
    strip=%(strip)s,
    upx=%(upx)s,
    upx_exclude=%(upx_exclude)s,
    name='%(name)s',
)
"""

cipher_absent_template = """
block_cipher = None
"""

cipher_init_template = """
block_cipher = pyi_crypto.PyiBlockCipher(key=%(key)r)
"""

bundleexetmplt = """app = BUNDLE(
    exe,
    name='%(name)s.app',
    icon=%(icon)s,
    bundle_identifier=%(bundle_identifier)s,
)
"""

bundletmplt = """app = BUNDLE(
    coll,
    name='%(name)s.app',
    icon=%(icon)s,
    bundle_identifier=%(bundle_identifier)s,
)
"""

splashtmpl = """splash = Splash(
    %(splash_image)r,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)
"""
