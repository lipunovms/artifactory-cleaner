#!/usr/bin/python3

import json
import time
import os
from datetime import datetime
import requests

if "SOCKS5_PROXY_HOST" in os.environ and "SOCKS5_PROXY_PORT" in os.environ:
    import socks
    import socket
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, os.environ["SOCKS5_PROXY_HOST"], int(os.environ["SOCKS5_PROXY_PORT"]))
    socket.socket = socks.socksocket

ARTIFACTORY_URL = os.environ["ARTIFACTORY_URL"]

ARTIFACTORY_TOKEN = os.environ["ARTIFACTORY_TOKEN"]

REPOSITORIES = os.environ["REPOSITORIES"].split(",")

if "SLEEP_SECONDS_BETWEEN_DELETION" in os.environ:
    SLEEP_SECONDS_BETWEEN_DELETION = float(os.environ["SLEEP_SECONDS_BETWEEN_DELETION"])
else:
    SLEEP_SECONDS_BETWEEN_DELETION = 0.1

if "GLOBAL_KEEP_DAYS" in os.environ:
    KEEP_ARTIFACT_CREATED = KEEP_ARTIFACT_DOWNLOADED = KEEP_ARTIFACT_UPDATED = KEEP_ARTIFACT_MODIFIED = int(os.environ["GLOBAL_KEEP_DAYS"])
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


def remove_artifacts(artifacts):
    for artifact in artifacts:
        if DRY_RUN != True:
            http_request_delete(ARTIFACTORY_URL+"/"+artifact)
            time.sleep(SLEEP_SECONDS_BETWEEN_DELETION)

            if SHOW_ARTIFACTS_LOG:
                print(artifact)
        else:
            if SHOW_ARTIFACTS_LOG:
                print(artifact)
            

def get_artifacts(repository):
    artifacts_json = http_request_post(ARTIFACTORY_URL+"/api/search/aql",data='items.find({"repo":"%s","type":"any"}).include("stat")' % repository)

    artifacts_to_delete = []
    size_to_delete = 0

    for artifact in artifacts_json["results"]:
        artifact_repo = artifact["repo"]
        artifact_path = artifact["path"]
        artifact_name = artifact["name"]
        artifact_type = artifact["type"]
        artifact_size = artifact["size"]
        artifact_created = datetime.strptime(artifact["created"], '%Y-%m-%dT%H:%M:%S.%fZ')
        artifact_updated = datetime.strptime(artifact["updated"], '%Y-%m-%dT%H:%M:%S.%fZ')
        artifact_modified = datetime.strptime(artifact["modified"], '%Y-%m-%dT%H:%M:%S.%fZ')

        artifact_downloaded = artifact["stats"][0].get("downloaded","never")
        if artifact_downloaded != "never": artifact_downloaded = datetime.strptime(artifact["stats"][0].get("downloaded","never"), '%Y-%m-%dT%H:%M:%S.%fZ')

        artifact_downloads = artifact["stats"][0]["downloads"]

        if artifact_downloaded != "never" and artifact_type != "folder":
            if artifact_name not in ARTIFACTS_BLACKLIST:
                downloaded_ago = datetime.today() - artifact_downloaded
                created_ago = datetime.today() - artifact_created
                updated_ago = datetime.today() - artifact_updated
                modified_ago = datetime.today() - artifact_modified

                if downloaded_ago.days > KEEP_ARTIFACT_DOWNLOADED and created_ago.days > KEEP_ARTIFACT_CREATED and updated_ago.days > KEEP_ARTIFACT_UPDATED and modified_ago.days > KEEP_ARTIFACT_MODIFIED:
                    artifacts_to_delete.append(artifact_repo+"/"+artifact_path+"/"+artifact_name)
                    size_to_delete = size_to_delete + int(artifact_size)

    return artifacts_to_delete,size_to_delete


for repository in REPOSITORIES:
    repository_info = http_request_get(ARTIFACTORY_URL+"/api/repositories/{}".format(repository))
    if repository_info["packageType"] in ["npm", "maven", "generic", "gems"]:
        artifacts_to_delete,size_to_delete = get_artifacts(repository)
        print(50*"#")
        print(repository,":",repository_info["packageType"], end=" : ")
        print(len(artifacts_to_delete)," artifacts, ",round(size_to_delete/1024/1024), " MB will be removed", sep="")
        
        remove_artifacts(artifacts_to_delete)
        print(len(artifacts_to_delete)," artifacts, ",round(size_to_delete/1024/1024), " MB were removed", sep="")
        print()
