import re, hashlib, pathlib
import sys


# update hashes in docker-compose.yml and return the current image tag
# usage: get_tag.py image path_to_hash path_to_hash ...


def get_hash(input_paths):
    """Get hash of Dockerfile input files or directories"""
    hasher = hashlib.sha256()
    for path in sorted(input_paths):
        path = pathlib.Path(path)
        if path.is_file():
            file_paths = [path]
        else:
            file_paths = sorted(p for p in path.glob('**/*') if p.is_file())
        for file_path in file_paths:
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()[:32]


def update_hash(image, hash, docker_compose_path='docker-compose.yml'):
    """Update image tag in docker_compose.yml, and return current image tag."""
    docker_compose_path = pathlib.Path(docker_compose_path)
    docker_compose = docker_compose_orig = docker_compose_path.read_text()

    # replace all instances of web:1-oldhash with web:2-newhash in docker_compose
    current_versions = re.findall(rf'image: {re.escape(image)}:(.*)', docker_compose)
    if not current_versions:
        raise ValueError(f'No image {image} found in docker-compose.yml')
    new_version = current_versions[0]
    digits = new_version.split('-')[0].split('.')
    digits[-1] = str(int(digits[-1]) + 1)
    new_version = "%s-%s" % (".".join(digits), hash)
    for current_version in current_versions:
        if hash not in current_version:
            docker_compose = docker_compose.replace(current_version, new_version)

    # write updates if any
    if docker_compose != docker_compose_orig:
        docker_compose_path.write_text(docker_compose)
        print("%s updated to version %s" % (docker_compose_path, new_version))
    else:
        print("%s is already up to date" % docker_compose_path)

    return new_version


def main(image, rebuild_paths, docker_compose_path='docker-compose.yml'):
    """Get hash based on paths that go into docker image, update docker image tag, and set current tag."""
    hash = get_hash(rebuild_paths)
    current_version = update_hash(image, hash, docker_compose_path)
    # string format to set steps.get-tag.outputs.tag if printed:
    return f"::set-output name=tag::{image}:{current_version}"
    
    
if __name__ == '__main__':
    image = sys.argv[1]
    rebuild_paths = sys.argv[2:]
    out = main(image, rebuild_paths)
    print(out)