# docker-compose-update-action

Github Action to update a docker image from a docker-compose.yml file and push to a repository.

Given a docker-compose.yml file like this:

```
    web:
        image: harvardlil/capstone:143-efd312bc82881d1da5ef46cebce39b4c
```

Use this action like this:

```
  - name: Rebuild harvardlil/capstone if necessary
    uses: harvard-lil/docker-compose-update-action@main
    with:
      working-directory: .
      image: "harvardlil/capstone"
      rebuild-if-changed: "Dockerfile requirements.txt yarn.lock"
      registry-user: ${{ secrets.REPOSITORY_USER }}
      registry-pass: ${{ secrets.REPOSITORY_TOKEN }}
```

The action will:

* Hash the contents of `rebuild-if-changed` (a list of files relative to `working-directory`)
  and compare the hash to `efd312bc82881d1da5ef46cebce39b4c`.
* If the hashes do not match, update the version number and hash in the tag in docker-compose.yml
  to `harvardlil/capstone:144-newhashnewhash`.
* If the new tag does not exist in the container registry, rebuild.
* If the action has sufficient permissions, push the new image to the registry.

Outputs:

* `image-tag`: the new image and tag, e.g. `"harvardlil/capstone:144-newhashnewhash"`
* `updated`: `"1"` if the new tag did not exist in the registry.