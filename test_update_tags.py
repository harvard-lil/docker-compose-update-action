from hashlib import sha256
from pathlib import Path
from random import shuffle
from shutil import copytree
from textwrap import dedent

import pytest

import update_tags


### test helpers ###

def hash_string(s):
    """Hash a string in the same way we hash file contents."""
    return sha256(s.encode('utf8')).hexdigest()[:32]


@pytest.fixture
def test_files(tmp_path):
    """Return path to a temp copy of the test_files directory."""
    test_files_path = tmp_path.joinpath('test_files')
    copytree(Path(__file__).parent / 'test_files', test_files_path)
    return test_files_path


### tests ###

def test_get_hash(tmp_path):
    # set up 10 files
    contents = 'abcdefghij'
    paths = [tmp_path / f'{c}.txt' for c in contents]
    for c, path in zip(contents, paths):
        path.write_text(c)

    # get_hash for list of paths returns hash of their contents concatenated
    shuffle(paths)
    assert update_tags.get_hash(paths, init_string='foo') == hash_string('fooabcdefghij')

    # get_hash for directory includes all files in directory
    assert update_tags.get_hash([tmp_path], init_string='foo') == hash_string('fooabcdefghij')


def test_main(test_files, monkeypatch):
    compose_path = test_files / 'docker-compose.yml'

    # patch remote_tag_exists to return False
    monkeypatch.setattr(update_tags, 'remote_tag_exists', lambda *args: False)

    # first run detects changes to toplevel and subdir
    out = update_tags.main(compose_path)
    assert out == f"::set-output name=services-to-rebuild::toplevel subdir"

    # no update the second time
    out = update_tags.main(compose_path)
    assert out == f"::set-output name=services-to-rebuild::"

    # 'push' action checks rebuild for all tags
    out = update_tags.main(compose_path, action='push')
    assert out == f"::set-output name=services-to-rebuild::toplevel subdir"

    # check hash values -- hashes are: build config, Dockerfile contents, x-hash-paths contents
    toplevel_hash = "bd018100e5b1c9159130decc1fa8884c"
    subdir_hash = "e6f9e079c6d2d933a50120f9b20ff869"
    assert toplevel_hash == hash_string(
        "{'context': '.', 'x-bake': {}, 'x-hash-paths': ['a.txt', 'subdir/b.txt']}" +
        '# toplevel\nFROM hello-world:latest' +
        'a' +
        'b'
    )
    assert subdir_hash == hash_string(
        "{'context': 'subdir', 'x-bake': {}, 'x-hash-paths': ['b.txt']}" +
        '# subdir\nFROM hello-world:latest' +
        'b'
    )

    # docker-compose.yml new contents
    assert compose_path.read_text().strip() == dedent(f"""
        services:
          toplevel:
            image: toplevel:0.2-{toplevel_hash}
          subdir:
            image: subdir:2-{subdir_hash}
    """).strip()

    # docker-compose.override.yml new contents
    assert compose_path.with_suffix('.override.yml').read_text().strip() == dedent(f"""
        services:
          toplevel:
            build:
              context: .
              x-bake:
                tags:
                  - toplevel:0.2-{toplevel_hash}
              x-hash-paths:
                - a.txt
                - subdir/b.txt
          subdir:
            build:
              context: subdir
              x-bake:
                tags:
                  - subdir:2-{subdir_hash}
              x-hash-paths:
                - b.txt
    """).strip()


def test_run_from_command_line(monkeypatch):
    def main_patch(docker_compose_path, action):
        assert docker_compose_path == 'foo/docker-compose.yml'
        assert action == 'push'
    monkeypatch.setattr("sys.argv", ["foo", "-a", "push", "-f", "foo/docker-compose.yml"])
    monkeypatch.setattr(update_tags, 'main', main_patch)
    update_tags.run_from_command_line()
