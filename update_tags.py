import re
import hashlib
import subprocess
import sys
from pathlib import Path
import os.path

import yaml


# update hashes in docker-compose.yml and docker-compose.override.yml, and return services affected by the update


def get_hash(input_paths, init_string=""):
    """Get hash of files or directories."""
    hasher = hashlib.sha256()
    print(init_string.encode('utf-8'))
    hasher.update(init_string.encode('utf-8'))
    for path in sorted(input_paths):
        path = Path(path)
        if path.is_file():
            file_paths = [path]
        else:
            if not path.is_dir():
                raise ValueError(f"{path} is not a file or directory")
            file_paths = sorted(p for p in path.glob('**/*') if p.is_file())
        for file_path in file_paths:
            print(file_path.read_bytes())
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()[:32]


def get_changed_tags(override_path, override_text):
    """
        Given text of docker-compose.override.yml, find all values of service.build.x-bake.tags that no longer match,
        based on hashing service.build itself, plus hashing Dockerfile, plus hashing all paths in service.build.x-hash-paths.
        Return list of (service_name, old_tag, new_tag) tuples,
        e.g. ("web", "harvardlil/web:1-oldhash", "harvardlil/web:2-newhash").
    """
    override_yaml = yaml.safe_load(override_text)
    changed_tags = []

    for service_name, service in override_yaml['services'].items():
        # only process services with an x-hash-paths setting
        if 'build' in service and 'x-hash-paths' in service['build']:
            build = service['build']
            tags = build['x-bake'].pop('tags')  # pop tags so they won't be included in hash

            # calculate new hash
            context = override_path.parent / build.get('context', '.')
            docker_file_path = os.path.join(context, build.get('dockerfile', 'Dockerfile'))
            hash_paths = sorted(set([docker_file_path] + [os.path.join(context, path) for path in build['x-hash-paths']]))
            hash = get_hash(hash_paths, init_string=str(service['build']))

            # if new hash isn't in current tag, calculate new tag
            old_tag = tags[0]
            if hash not in old_tag:
                image_name, image_tag = old_tag.split(':', 1)
                digits, old_hash = image_tag.split('-', 1)
                digits = digits.split('.')
                digits[-1] = str(int(digits[-1]) + 1)
                new_tag = f"{image_name}:{'.'.join(digits)}-{hash}"
                changed_tags.append((service_name, old_tag, new_tag))

    return changed_tags


def remote_tag_exists(tag):
    """Check if a remote docker tag exists."""
    return subprocess.run(['docker', 'manifest', 'inspect', tag], check=True).returncode == 1


def main(docker_compose_path='docker-compose.yml'):
    """Get hash based on paths that go into docker image, update docker image tag, and set current tag."""
    # load docker-compose.yml and docker-compose.override.yml files
    docker_compose_path = Path(docker_compose_path)
    docker_compose_text = docker_compose_path.read_text()
    override_path = docker_compose_path.with_suffix('.override.yml')
    override_text = override_path.read_text()
    changed_tags = get_changed_tags(override_path, override_text)
    to_rebuild = []

    if changed_tags:
        # write updated tags to docker-compose.yml and docker-compose.override.yml
        for service_name, old_tag, new_tag in changed_tags:
            docker_compose_text = docker_compose_text.replace(old_tag, new_tag)
            override_text = override_text.replace(old_tag, new_tag)
            if not remote_tag_exists(new_tag):
                to_rebuild.append(service_name)
        docker_compose_path.write_text(docker_compose_text)
        override_path.write_text(override_text)

    # string format to set steps.get-tag.outputs.rebuild_services if printed:
    return f"::set-output name=services-to-rebuild::{' '.join(to_rebuild)}"


if __name__ == '__main__':
    docker_compose_path = sys.argv[1] if len(sys.argv) > 1 else 'docker-compose.yml'
    out = main(docker_compose_path)
    print(out)