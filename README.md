# food-health

Python toolkit for personal measurements, training, nutrition, and household food operations.

**Privacy:** This GitHub repository is PUBLIC. Personal measurements, receipts, private archives, and extracts must remain local or in permission-controlled Google Drive. Never commit raw personal records. Google Sheets **Personal Measurements** is the canonical measurement source.

## Workstation

The local Git working tree is `~/Documents/food`. The original 89 files are safely in `archive/legacy/` (ignored by Git), with a local SHA-256 manifest.

```bash
cd ~/Documents/food
PYTHONPATH=src python3 -m food_health doctor
PYTHONPATH=src python3 -m unittest discover -s tests -v
# Optional:
python3 -m pip install -e .
```

No automatic writes to Google Sheets, processing of private data, background jobs, or credential access happen in this bootstrap.

See `docs/architecture.md` and `docs/migration_map.md`.
