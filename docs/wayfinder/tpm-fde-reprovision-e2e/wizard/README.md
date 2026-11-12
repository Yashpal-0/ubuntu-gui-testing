# Golden checkpoint export

Run once, with sudo, from the `ubuntu-gui-testing` checkout:

```bash
sudo ./docs/wayfinder/tpm-fde-reprovision-e2e/wizard/export-golden.py
```

It requires `tpm-fde-test2` to be shut off, then copies its disk (9.9 GiB), UEFI NVRAM, swtpm state and domain XML into `~/.local/share/ugt-fde/golden/tpm-fde-test2-<UTC>`, verifies every SHA-256, writes `metadata.json` with paths and hashes only, chowns the tree to you with `0700`/`0600` modes, and leaves the source shut off and unchanged. Preview with `--check` (no sudo). Re-run with `--force` to keep an older export as `.replaced.<timestamp>`. Expect 2–5 minutes and about 10 GiB.

After it finishes, point the FDE fixture at the printed `metadata.json`. The tree contains the encrypted disk and TPM state: treat it as secret, never copy it into the repo or artifacts.
