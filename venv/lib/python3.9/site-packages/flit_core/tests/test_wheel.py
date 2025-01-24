from pathlib import Path
from zipfile import ZipFile

from testpath import assert_isfile

from flit_core.wheel import make_wheel_in, main

samples_dir = Path(__file__).parent / 'samples'

def test_licenses_dir(tmp_path):
    # Smoketest for https://github.com/pypa/flit/issues/399
    info = make_wheel_in(samples_dir / 'inclusion' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)


def test_source_date_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '1633007882')
    info = make_wheel_in(samples_dir / 'pep621' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(info.file, 'r') as zf:
        assert zf.getinfo('module1a.py').date_time[:3] == (2021, 9, 30)


def test_zero_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '0')
    info = make_wheel_in(samples_dir / 'pep621' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(info.file, 'r') as zf:
        assert zf.getinfo('module1a.py').date_time == (1980, 1, 1, 0, 0, 0)


def test_main(tmp_path):
    main(['--outdir', str(tmp_path), str(samples_dir / 'pep621')])
    wheels = list(tmp_path.glob('*.whl'))
    assert len(wheels) == 1
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(wheels[0], 'r') as zf:
        assert 'module1a.py' in zf.namelist()

        
def test_data_dir(tmp_path):
    info = make_wheel_in(samples_dir / 'with_data_dir' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    with ZipFile(info.file, 'r') as zf:
        assert 'module1-0.1.data/data/share/man/man1/foo.1' in zf.namelist()
