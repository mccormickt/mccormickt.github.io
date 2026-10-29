# [mccormickt.github.io](https://mccormickt.github.io)

Holds the source of my personal blog made using [hugo](https://gohugo.io) and deployed with Github actions.

## Standard.site on ATProto

The site publishes [Standard.site](https://standard.site/docs/) records under the
`jan0ski.net` ATProto account. GitHub Pages remains the canonical website.

Hugo generates:

- `/.well-known/site.standard.publication` to verify the publication.
- Publication discovery links and per-post document verification links in the HTML head.
- `/standard.json` with one publication record and all published posts, including
  plain text from rendered shortcodes. Drafts and future posts are excluded.

The account DID and publication key are set in `hugo.toml`. Document keys are
SHA-256 hashes of their canonical URLs. Keep the base URL and post URLs stable
to retain the same record identities.

### Enable publishing

1. Create an app password for `jan0ski.net` in
   [Bluesky app password settings](https://bsky.app/settings/app-passwords).
   Direct message access is not needed. Do not use the account password.
2. Add it as the `ATPROTO_APP_PASSWORD` repository secret in
   [GitHub Actions secrets](https://github.com/mccormickt/mccormickt.github.io/settings/secrets/actions).
3. Deploy the changes through the Pages workflow. After each successful deployment,
   the sync job discovers the account's PDS and creates or updates its records.
   Without the secret, the website still deploys and sync is skipped with a notice.

The sync owns the generated records and replaces their contents on updates.
It skips unchanged records and does not delete records. If a post is removed,
made private, or moved to a new URL, remove its old ATProto record separately.
Publishing Standard.site records does not create Bluesky feed posts.

### Local checks

With Hugo 0.167.0 extended, Python 3, and the theme submodule installed:

```sh
git submodule update --init --recursive
python3 -m unittest discover -s tests
hugo --minify
python3 scripts/sync-standard-site.py
```

The sync command defaults to a dry run and makes no network requests. To publish
manually, provide `ATPROTO_APP_PASSWORD` through your secret manager and run
`python3 scripts/sync-standard-site.py --publish`. Never commit the password.
