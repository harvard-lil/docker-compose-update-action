from hashlib import sha256
from random import shuffle
import pytest

from get_tag import get_hash, update_hash, main


### test helpers ###

def hash_string(s):
    """Hash a string in the same way we hash file contents."""
    return sha256(s.encode('utf8')).hexdigest()[:32]


@pytest.fixture
def project_files(tmp_path):
    files_path = tmp_path.joinpath('files')
    files_path.mkdir()
    contents = 'abcdefghij'
    paths = [files_path / f'{c}.txt' for c in contents]
    for c, path in zip(contents, paths):
        path.write_text(c)
    return paths


@pytest.fixture
def docker_compose_yml(tmp_path):
    docker_compose_path = tmp_path.joinpath('docker-compose.yml')
    docker_compose_path.write_text("""
        services:
            db:
                image: harvardlil/db:0.1-oldhash
            web:
                image: harvardlil/web:1-oldhash
            web2:
                image: harvardlil/web:1-oldhash
    """)
    return docker_compose_path


### tests ###

def test_get_hash(tmp_path, project_files):
    # get_hash for list of paths returns hash of their contents concatenated
    shuffle(project_files)
    assert get_hash(project_files) == hash_string('abcdefghij')

    # get_hash for directory includes all files in directory
    assert get_hash([tmp_path.joinpath('files')]) == hash_string('abcdefghij')


def test_update_hash(docker_compose_yml):
    # update hashes and version numbers
    update_hash('harvardlil/db', 'newdbhash', docker_compose_yml)
    update_hash('harvardlil/web', 'newwebhash', docker_compose_yml)

    # repetition doesn't increment number
    update_hash('harvardlil/web', 'newwebhash', docker_compose_yml)

    assert docker_compose_yml.read_text() == """
        services:
            db:
                image: harvardlil/db:0.2-newdbhash
            web:
                image: harvardlil/web:2-newwebhash
            web2:
                image: harvardlil/web:2-newwebhash
    """


def test_main(project_files, docker_compose_yml):
    out = main('harvardlil/db', project_files[0:5], docker_compose_yml)
    assert out == f"::set-output name=tag::harvardlil/db:0.2-36bbe50ed96841d10443bcb670d6554f"
    out = main('harvardlil/web', project_files[5:10], docker_compose_yml)
    assert out == f"::set-output name=tag::harvardlil/web:2-7272207e4b9c7e929f4278d245c77683"

    assert docker_compose_yml.read_text() == """
        services:
            db:
                image: harvardlil/db:0.2-36bbe50ed96841d10443bcb670d6554f
            web:
                image: harvardlil/web:2-7272207e4b9c7e929f4278d245c77683
            web2:
                image: harvardlil/web:2-7272207e4b9c7e929f4278d245c77683
    """