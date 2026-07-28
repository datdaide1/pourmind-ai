# Data Pipeline

Reproducible preparation and Qdrant ingestion for the cocktail catalog.

## Data domains

- cocktails and ingredients;
- mixology references;
- liquor prices;
- venues.

Raw snapshots live in `data/crawled-data/`; normalized outputs live in `data/cleaned/`. Review source permissions and attribution before redistributing any crawled dataset.

## Setup

From the repository root, create `.env` from `.env.example`, then:

```bash
cd pipelines/knowledge-base
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Workflow

```bash
# Inspect and normalize raw files
python scripts/inspect_raw_data.py
python scripts/clean_data.py

# Validate deterministic cleaning behavior
python scripts/test_cleaning.py

# Create or update the Qdrant collection
python scripts/setup_qdrant_pipeline.py

# Verify ingestion and metadata filtering
python scripts/verify_qdrant_setup.py
python scripts/test_metadata_filtering.py
```

Qdrant operations require `QDRANT_URL` and, for hosted clusters, `QDRANT_API_KEY`. Embedding behavior and external uploads may require additional credentials defined in `.env.example`.

## Script categories

- `clean_data.py`: normalization and cleaned dataset generation
- `inspect_*.py`, `rating_stats.py`, `find_reviews.py`: data exploration and quality checks
- `setup_qdrant_pipeline.py`: embedding and vector ingestion
- `verify_qdrant_setup.py`, `test_metadata_filtering.py`: post-ingestion verification
- `upload_braintrust_dataset.py`: optional evaluation dataset publishing

Scripts that write to hosted services should be run deliberately and never from basic CI.
