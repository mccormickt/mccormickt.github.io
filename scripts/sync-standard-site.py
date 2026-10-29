#!/usr/bin/env python3
"""Publish Hugo's Standard.site records to the configured ATProto account."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(url, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default="public/standard.json")
    parser.add_argument(
        "--publish", action="store_true", help="Write records to ATProto"
    )
    args = parser.parse_args()
    with open(args.manifest) as source:
        manifest = json.load(source)

    did = manifest["did"]
    records = manifest["records"]
    if not args.publish:
        print(f"Dry run: {len(records)} records for {did}; no network requests made.")
        return

    password = os.environ.get("ATPROTO_APP_PASSWORD")
    if not password:
        raise ValueError("Set ATPROTO_APP_PASSWORD before publishing.")
    identity = request(f"https://plc.directory/{did}")
    pds = next(
        service["serviceEndpoint"].rstrip("/")
        for service in identity["service"]
        if service["id"] == "#atproto_pds"
    )
    session = request(
        f"{pds}/xrpc/com.atproto.server.createSession",
        {"identifier": did, "password": password},
    )
    if session["did"] != did:
        raise ValueError("The authenticated account does not match the configured DID.")
    token = session["accessJwt"]
    for entry in records:
        params = {"repo": did, "collection": entry["collection"], "rkey": entry["rkey"]}
        try:
            current = request(
                f"{pds}/xrpc/com.atproto.repo.getRecord?{urlencode(params)}",
                token=token,
            )
        except HTTPError as error:
            if error.code not in (400, 404):
                raise
            details = json.load(error)
            if details.get("error") != "RecordNotFound":
                raise
        else:
            if current["value"] == entry["record"]:
                print(f"Unchanged: {entry['collection']}/{entry['rkey']}")
                continue
        request(
            f"{pds}/xrpc/com.atproto.repo.putRecord",
            {**params, "record": entry["record"]},
            token,
        )
        print(f"Published: {entry['collection']}/{entry['rkey']}")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit(f"ATProto request failed (HTTP {error.code}).")
    except (URLError, ValueError, KeyError, StopIteration) as error:
        sys.exit(f"Standard.site sync failed: {error}")
