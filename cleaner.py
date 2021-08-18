#!/usr/bin/python3

import json
import time
import os
from datetime import datetime, timezone
import requests
from prettytable import PrettyTable
from packaging import version

if "SOCKS5_PROXY_HOST" in os.environ and "SOCKS5_PROXY_PORT" in os.environ:
    import socks
    import socket
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, os.environ["SOCKS5_PROXY_HOST"], int(os.environ["SOCKS5_PROXY_PORT"]))
    socket.socket = socks.socksocket

ARTIFACTORY_URL = os.environ["ARTIFACTORY_URL"]
ARTIFACTORY_TOKEN = os.environ["ARTIFACTORY_TOKEN"]
REPOSITORIES = os.environ["REPOSITORIES"].split(",")

if "ARTIFACTS_FILTER" in os.environ:
    ARTIFACTS_FILTER = os.environ["ARTIFACTS_FILTER"]
    if ARTIFACTS_FILTER == '""' or ARTIFACTS_FILTER == "''":
        ARTIFACTS_FILTER = ""
else:
    ARTIFACTS_FILTER = ""

if "SLEEP_SECONDS_BETWEEN_DELETION" in os.environ:
    SLEEP_SECONDS_BETWEEN_DELETION = float(os.environ["SLEEP_SECONDS_BETWEEN_DELETION"])
else:
    SLEEP_SECONDS_BETWEEN_DELETION = 0.1

if "KEEP_ARTIFACT_GLOBAL" in os.environ:
    KEEP_ARTIFACT_CREATED = KEEP_ARTIFACT_DOWNLOADED = KEEP_ARTIFACT_UPDATED = KEEP_ARTIFACT_MODIFIED = int(os.environ["KEEP_ARTIFACT_GLOBAL"])
else:
    KEEP_ARTIFACT_CREATED = int(os.environ["KEEP_ARTIFACT_CREATED"])
    KEEP_ARTIFACT_DOWNLOADED = int(os.environ["KEEP_ARTIFACT_DOWNLOADED"])
    KEEP_ARTIFACT_UPDATED = int(os.environ["KEEP_ARTIFACT_UPDATED"])
    KEEP_ARTIFACT_MODIFIED = int(os.environ["KEEP_ARTIFACT_MODIFIED"])

if "ARTIFACTS_BLACKLIST" in os.environ:
    ARTIFACTS_BLACKLIST = os.environ["ARTIFACTS_BLACKLIST"].split(",")
else:
    ARTIFACTS_BLACKLIST = []

if os.environ["DRY_RUN"].lower() in ["true", "1", "yes"]:
    DRY_RUN = True
else:
    DRY_RUN = False

if os.environ["EMPTY_TRASH_CAN"].lower() in ["true", "1", "yes"]:
    EMPTY_TRASH_CAN = True
else:
    EMPTY_TRASH_CAN = False

if os.environ["RUN_GARBAGE_COLLECTION"].lower() in ["true", "1", "yes"]:
    RUN_GARBAGE_COLLECTION = True
else:
    RUN_GARBAGE_COLLECTION = False

if os.environ["SHOW_ARTIFACTS_LOG"].lower() in ["true", "1", "yes"]:
    SHOW_ARTIFACTS_LOG = True
else:
    SHOW_ARTIFACTS_LOG = False

def http_request_post(url, data=None):
    headers = { 'X-JFrog-Art-Api' : ARTIFACTORY_TOKEN, 'Content-Type': 'text/plain' }    
    response = requests.post(url, headers=headers, data=data, verify=False)

    return(json.loads(response.content.decode("utf-8")))


def http_request_get(url):
    headers = { 'X-JFrog-Art-Api' : ARTIFACTORY_TOKEN, 'Content-Type': 'application/json' }    
    response = requests.get(url, headers=headers, verify=False)

    return(json.loads(response.content.decode("utf-8")))


def http_request_delete(url, data=None):
    headers = { 'X-JFrog-Art-Api' : ARTIFACTORY_TOKEN, 'Content-Type': 'text/plain' }    
    response = requests.delete(url, headers=headers, data=data, verify=False)


def empty_trash_can():
    headers = { 'X-JFrog-Art-Api' : ARTIFACTORY_TOKEN, 'Content-Type': 'text/plain' }
    requests.post(ARTIFACTORY_URL+"/api/trash/empty", headers=headers, data=None, verify=False)


def run_garbage_collection():
    headers = { 'X-JFrog-Art-Api' : ARTIFACTORY_TOKEN, 'Content-Type': 'text/plain' }
    requests.post(ARTIFACTORY_URL+"/api/system/storage/gc", headers=headers, data=None, verify=False)


def remove_artifacts(artifacts, repo_type):
    for artifact,downloaded_ago in artifacts.items():
        if repo_type == "docker":
            artifact = artifact.replace("/manifest.json","")

        if DRY_RUN != True:
            http_request_delete(ARTIFACTORY_URL+"/"+artifact)
            time.sleep(SLEEP_SECONDS_BETWEEN_DELETION)

            if SHOW_ARTIFACTS_LOG:
                print(downloaded_ago, artifact)
        else:
            if SHOW_ARTIFACTS_LOG:
                print(downloaded_ago, artifact)


def get_artifacts(repository,repo_type=None):
    if artifactory_version <= version.parse("6.1.0"):
        datetime_format = '%Y-%m-%dT%H:%M:%S.%f%z'
        tz = timezone.utc
    else:
        datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        tz = None

    if repo_type == 'docker':
        artifacts_filter = '"name":"manifest.json"'
    else:
        artifacts_filter = '"type":"any"'

    artifacts_json = http_request_post(ARTIFACTORY_URL+"/api/search/aql",data='items.find({"repo":"%s",%s}).include("stat")' % (repository, artifacts_filter))

    artifacts_to_delete = {}
    size_to_delete = 0

    for artifact in artifacts_json["results"]:
        artifact_repo = artifact["repo"]
        artifact_path = artifact["path"]
        artifact_name = artifact["name"]
        artifact_type = artifact["type"]
        artifact_size = artifact["size"]
        artifact_created = datetime.strptime(artifact["created"], datetime_format)
        artifact_updated = datetime.strptime(artifact["updated"], datetime_format)
        artifact_modified = datetime.strptime(artifact["modified"], datetime_format)

        artifact_downloaded = artifact["stats"][0].get("downloaded","never")
        if artifact_downloaded != "never":
            artifact_downloaded = datetime.strptime(artifact["stats"][0].get("downloaded","never"), datetime_format)
        else:
            artifact_downloaded = artifact_created

        artifact_downloads = artifact["stats"][0]["downloads"]

        if artifact_type != "folder":
            if artifact_name not in ARTIFACTS_BLACKLIST:

                downloaded_ago = datetime.now(tz) - artifact_downloaded
                created_ago = datetime.now(tz) - artifact_created
                updated_ago = datetime.now(tz) - artifact_updated
                modified_ago = datetime.now(tz) - artifact_modified

                if downloaded_ago.days > KEEP_ARTIFACT_DOWNLOADED and created_ago.days > KEEP_ARTIFACT_CREATED and updated_ago.days > KEEP_ARTIFACT_UPDATED and modified_ago.days > KEEP_ARTIFACT_MODIFIED:
                    full_artifact_path = artifact_repo+"/"+artifact_path+"/"+artifact_name

                    if ARTIFACTS_FILTER:
                        if ARTIFACTS_FILTER in full_artifact_path:
                            artifacts_to_delete[full_artifact_path] = downloaded_ago.days
                            size_to_delete = size_to_delete + int(artifact_size)
                    else:
                        artifacts_to_delete[full_artifact_path] = downloaded_ago.days
                        size_to_delete = size_to_delete + int(artifact_size)
                
                    

    artifacts_to_delete = {k: v for k, v in sorted(artifacts_to_delete.items(), key=lambda item: item[1])}
    return artifacts_to_delete,size_to_delete


artifactory_version = version.parse(http_request_get(ARTIFACTORY_URL+"/api/system/version")["version"])

statistics = PrettyTable()
statistics.field_names = ["Repositry", "Repository type", "Artifacts deleted", "MB deleted"]

for repository in REPOSITORIES:
    repository_info = http_request_get(ARTIFACTORY_URL+"/api/repositories/{}".format(repository))
    if repository_info["packageType"] in ["npm", "maven", "generic", "gems", "docker"]:
        repo_type = repository_info["packageType"]
        artifacts_to_delete,size_to_delete = get_artifacts(repository, repo_type)
        
        print(50*"#")
        print("Repository: ", repository, ", Type: ", repo_type)

        remove_artifacts(artifacts_to_delete, repo_type)

        if repo_type == "docker":
            statistics.add_row([repository, repo_type, len(artifacts_to_delete), "?"])
        else:
            statistics.add_row([repository, repo_type, len(artifacts_to_delete), round(size_to_delete/1024/1024)])
        print()

if EMPTY_TRASH_CAN:
    empty_trash_can()
    time.sleep(5)

if RUN_GARBAGE_COLLECTION:
    run_garbage_collection()

statistics.sortby = "Artifacts deleted"
statistics.reversesort = True
print(statistics)

print("DRY_RUN=", DRY_RUN, sep="")
print("ARTIFACTS_FILTER=", ARTIFACTS_FILTER, sep="")
for k, v in os.environ.items():
    if "KEEP_ARTIFACT_" in k:
        print(f'{k}={v}')

