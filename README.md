# docker-compose-update-action

Github Action to update docker images from a docker-compose.yml file and push to a repository.

Given a docker-compose.yml file like this:

```
    web:
        image: harvardlil/capstone:10-efd312bc82881d1da5ef46cebce39b4c
    db:
        image: harvardlil/capstone-db:0.2-d8509b42e874e7d71bdb89edf5e7e01b
```

And a docker-compose.override.yml like this:

```
    services:
        web:
            build:
                context: .
                cache_from:
                  - type: registry
                  - ref: "registry.lil.tools/harvardlil/cap-db:buildcache"
                cache_to:
                  - type: registry
                  - ref: "registry.lil.tools/harvardlil/cap-db:buildcache,type=max"
                x-bake:
                    tags:
                        - harvardlil/capstone:10-efd312bc82881d1da5ef46cebce39b4c
                x-hash-paths:
                    - foo.txt
        db:
            build:
                context: .
                cache_from:
                  - type: registry
                  - ref: "registry.lil.tools/harvardlil/cap-db:buildcache"
                cache_to:
                  - type: registry
                  - ref: "registry.lil.tools/harvardlil/cap-db:buildcache,type=max"
                x-bake:
                    tags:
                        - harvardlil/capstone-db:0.2-d8509b42e874e7d71bdb89edf5e7e01b
                x-hash-paths:
                    - bar.txt
```

Use this action like this:

```
  - name: Rebuild docker images if necessary
    uses: harvard-lil/docker-compose-update-action@main
```

For each service with an x-hash-paths section in docker-compose.override.yml, the action will:

* Hash the contents of the `build` section of the docker-compose.override.yml service, the
  Dockerfile, and the files specified in the `x-hash-paths` section.
* Compare the hash to the hash in the `tags` section of the docker-compose.override.yml service.
* If the hashes do not match, update the version number and hash in both the docker-compose.yml
  and docker-compose.override.yml files.
* If the new tag does not exist in the container registry, rebuild.

By default the action will load new images to the local docker cache. If you want to push the
images to the registry instead, add `bake-action: push` and registry credentials. The event name
must be `push` for this to work:

```
  - name: Rebuild docker images if necessary
    uses: harvard-lil/docker-compose-update-action@main
    with:
      registry: docker.io
      registry-user: ${{ secrets.REGISTRY_USER }}
      registry-pass: ${{ secrets.REGISTRY_TOKEN }}
      bake-action: push
```

Outputs:

* `services-rebuilt`: the list of services with updated tags, e.g. `"web db"`.
