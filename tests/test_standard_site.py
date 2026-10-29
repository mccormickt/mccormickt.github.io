import contextlib
import copy
import io
import json
import os
import runpy
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DID = "did:plc:mfolp7m237wqh3mrtjpsvbxm"
PUBLICATION = f"at://{DID}/site.standard.publication/blog.jan0ski.net"


class Links(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links = {}
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link":
            self.links[attrs.get("rel")] = attrs.get("href")


class StandardSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        content = Path(cls.temp.name) / "content"
        (content / "post").mkdir(parents=True)
        (content / "post" / "example.md").write_text(
            "+++\ntitle = 'A post & café'\ndate = '2020-04-16T21:19:00-05:00'\n"
            "tags = ['golang', 'security']\n+++\n## Example\n"
            '{{< include "shellcode_injection.go" "9:19" >}}\n'
        )
        (content / "post" / "untagged.md").write_text(
            "+++\ntitle = 'Untagged'\ndate = '2021-01-01T00:00:00Z'\n+++\nPlain text.\n"
        )
        for name, fields in (
            ("draft", "draft = true"),
            ("future", "date = '2099-01-01T00:00:00Z'"),
        ):
            (content / "post" / f"{name}.md").write_text(
                f"+++\ntitle = '{name}'\n{fields}\n+++\nNot published.\n"
            )
        cls.public = Path(cls.temp.name) / "public"
        subprocess.run(
            [
                "hugo",
                "--minify",
                "--contentDir",
                str(content),
                "--destination",
                str(cls.public),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.manifest_path = cls.public / "standard.json"
        cls.manifest = json.loads(cls.manifest_path.read_text())

    def test_records_and_verification_match_published_pages(self):
        self.assertEqual(self.manifest["did"], DID)
        publication, *documents = self.manifest["records"]
        self.assertEqual(publication["record"]["url"], "https://blog.jan0ski.net")
        self.assertEqual(
            {e["record"]["path"] for e in documents},
            {"/post/example/", "/post/untagged/"},
        )
        self.assertEqual(
            (self.public / ".well-known/site.standard.publication").read_text(),
            PUBLICATION,
        )
        for entry in documents:
            record = entry["record"]
            self.assertEqual(record["site"], PUBLICATION)
            self.assertEqual(entry["collection"], "site.standard.document")
            uri = f"at://{DID}/site.standard.document/{entry['rkey']}"
            links = Links(self.public / record["path"].lstrip("/") / "index.html").links
            self.assertEqual(links["site.standard.document"], uri)
            self.assertEqual(links["site.standard.publication"], PUBLICATION)
        home = Links(self.public / "index.html").links
        self.assertNotIn("site.standard.document", home)
        example = next(
            e["record"] for e in documents if e["record"]["path"] == "/post/example/"
        )
        self.assertEqual(example["title"], "A post & café")
        self.assertEqual(example["publishedAt"], "2020-04-17T02:19:00Z")
        self.assertEqual(example["tags"], ["golang", "security"])
        self.assertIn("VirtualAlloc", example["textContent"])
        self.assertNotIn("{{< include", example["textContent"])
        untagged = next(
            e["record"] for e in documents if e["record"]["path"] == "/post/untagged/"
        )
        self.assertEqual(untagged["tags"], [])

    def run_sync(self, publish=False):
        args = ["sync-standard-site.py", str(self.manifest_path)]
        if publish:
            args.append("--publish")
        output = io.StringIO()
        with patch("sys.argv", args), contextlib.redirect_stdout(output):
            runpy.run_path(
                str(ROOT / "scripts/sync-standard-site.py"), run_name="__main__"
            )
        return output.getvalue()

    def test_dry_run_has_no_network_access(self):
        with patch(
            "urllib.request.urlopen", side_effect=AssertionError("Network access")
        ):
            self.assertIn("Dry run: 3 records", self.run_sync())

    def test_publish_creates_updates_and_skips_unchanged_records(self):
        repo = {("site.standard.publication", "another-site"): {"name": "Keep me"}}
        revisions = []

        def pds(request, timeout):
            url = urlparse(
                request.full_url if hasattr(request, "full_url") else request
            )
            body = (
                json.loads(request.data)
                if hasattr(request, "data") and request.data
                else None
            )
            if url.hostname == "plc.directory":
                result = {
                    "service": [
                        {"id": "#atproto_pds", "serviceEndpoint": "https://pds.test"}
                    ]
                }
            elif url.path.endswith("createSession"):
                if body != {"identifier": DID, "password": "test-password"}:
                    raise AssertionError("Invalid credentials")
                result = {"did": DID, "accessJwt": "test-token"}
            else:
                self.assertEqual(
                    request.get_header("Authorization"), "Bearer test-token"
                )
                if url.path.endswith("getRecord"):
                    query = parse_qs(url.query)
                    key = (query["collection"][0], query["rkey"][0])
                    if key not in repo:
                        raise HTTPError(
                            request.full_url,
                            400,
                            "Missing",
                            {},
                            io.BytesIO(b'{"error":"RecordNotFound"}'),
                        )
                    result = {"value": repo[key]}
                elif url.path.endswith("putRecord"):
                    self.assertEqual(body["repo"], DID)
                    key = (body["collection"], body["rkey"])
                    repo[key] = body["record"]
                    revisions.append(copy.deepcopy(repo))
                    result = {"uri": f"at://{DID}/{key[0]}/{key[1]}"}
                else:
                    raise AssertionError(f"Unexpected endpoint: {url.path}")
            return io.BytesIO(json.dumps(result).encode())

        with (
            patch.dict(os.environ, ATPROTO_APP_PASSWORD="test-password"),
            patch("urllib.request.urlopen", pds),
        ):
            self.run_sync(publish=True)
            for entry in self.manifest["records"]:
                self.assertEqual(
                    repo[(entry["collection"], entry["rkey"])], entry["record"]
                )
            self.assertEqual(len(revisions), 3)
            self.run_sync(publish=True)
            self.assertEqual(len(revisions), 3)
            publication = self.manifest["records"][0]
            key = (publication["collection"], publication["rkey"])
            repo[key] = {**repo[key], "name": "Outdated title"}
            self.run_sync(publish=True)
            self.assertEqual(len(revisions), 4)
            self.assertEqual(repo[key], publication["record"])
            self.assertEqual(
                repo[("site.standard.publication", "another-site")], {"name": "Keep me"}
            )

    def test_authentication_failure_does_not_publish(self):
        def reject(request, timeout):
            if urlparse(request.full_url).hostname == "plc.directory":
                return io.BytesIO(
                    b'{"service":[{"id":"#atproto_pds","serviceEndpoint":"https://pds.test"}]}'
                )
            if request.full_url.endswith("createSession"):
                raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO())
            raise AssertionError("Repository access after failed authentication")

        with (
            patch.dict(os.environ, ATPROTO_APP_PASSWORD="test-password"),
            patch("urllib.request.urlopen", reject),
            self.assertRaisesRegex(SystemExit, r"HTTP 401"),
        ):
            self.run_sync(publish=True)
