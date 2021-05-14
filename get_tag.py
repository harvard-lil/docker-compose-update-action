import re, hashlib, pathlib
import sys

# usage: get_tag.py image file_to_hash file_to_hash ...
image = sys.argv[1]
rebuild_if_changed = sys.argv[2:]

# get hash of Dockerfile input files
hasher = hashlib.sha256()
for path in rebuild_if_changed:
    hasher.update(pathlib.Path(path).read_bytes())
hash = hasher.hexdigest()[:32]

# see if hash appears in docker-compose.yml
docker_compose_path = pathlib.Path('docker-compose.yml')
docker_compose = docker_compose_path.read_text()
current_version = re.findall(rf'image: {re.escape(image)}:(.*)', docker_compose)[0]
if hash not in docker_compose:

    # if hash not found, increment image version number, append new hash, and insert
    digits = current_version.split('-')[0].split('.')
    digits[-1] = str(int(digits[-1]) + 1)
    new_version = "%s-%s" % (".".join(digits), hash)
    docker_compose = docker_compose.replace(current_version, new_version)
    docker_compose_path.write_text(docker_compose)
    print("%s updated to version %s" % (docker_compose_path, new_version))
    current_version = new_version

else:
    print("%s is already up to date" % docker_compose_path)

print(f"::set-output name=tag::{image}:{current_version}")