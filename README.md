## Artifactory cleaner
It removes old artifacts from your artifactory server. Available types of repositories(tested): maven, npm, gems, generic.

## How to use:
`docker-compose up`

or you can use ready image

```
docker run -e ARTIFACTORY_URL=https://your.artifactory.com/artifactory \
-e ARTIFACTORY_TOKEN=your_token \
-e SLEEP_SECONDS_BETWEEN_DELETION=0.05 \
-e DRY_RUN=True \
-e REPOSITORIES=your_repo \
-e GLOBAL_KEEP_DAYS=180 \
-e SHOW_ARTIFACTS_LOG=True \
lipunovms/artifactory_cleaner:latest
```

## Environment variables:

- ARTIFACTORY_URL - artifactory url
- ARTIFACTORY_TOKEN - artifactory access token
- REPOSITORIES=repo1,repo2 - repositories list comma-separated (without spaces)
- SLEEP_SECONDS_BETWEEN_DELETION - time between artifacts deletion in seconds(default: 0.1)
- DRY_RUN - dry run mode, just to show information and artifacts will be deleted (available values: True or False, default: False)
- SHOW_ARTIFACTS_LOG - show in logs artifacts that will be deleted (available values: True or False, default: False)
- KEEP_ARTIFACT_CREATED - how many days to store orienting to artifact`s creation date
- KEEP_ARTIFACT_DOWNLOADED - how many days to store orienting to artifact`s last download date
- KEEP_ARTIFACT_UPDATED - how many days to store orienting to artifact`s updation date
- KEEP_ARTIFACT_MODIFIED - how many days to store orienting to artifact`s modification date
- GLOBAL_KEEP_DAYS - how many days to store, this variable overrides previous KEEP_ARTIFACT-* variables and can be used instead
- ARTIFACTS_BLACKLIST - artifacts list comma-separated(without spaces) that will ignored
- SOCKS5_PROXY_HOST - socks5 proxy host (proxy used if both SOCKS5_PROXY_HOST and SOCKS5_PROXY_PORT are defined)
- SOCKS5_PROXY_PORT socks5 proxy port (proxy used if both SOCKS5_PROXY_HOST and SOCKS5_PROXY_PORT are defined)

