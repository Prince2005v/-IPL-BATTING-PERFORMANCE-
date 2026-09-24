# IPL Data Analyst

Small project to parse IPL match JSON files and produce CSV summaries.

Getting started

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the processing script from the project root:

```bash
python notebooks/read_ipl.py
```

Notes
- Place raw JSON match files in `data/ipl_json/` or extract `ipl_json.zip` there.
- Output CSVs are written into the `data/` directory.
