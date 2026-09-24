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

- Tech stack
## 🛠️ Tech Stack

- Python
- Pandas
- SQLite
- SQL
- Tableau Public
- Git & GitHub
Project workflow
## 🔄 Project Workflow

Raw IPL JSON
     ↓
Python + Pandas
     ↓
Data Cleaning & Transformation
     ↓
CSV Analytical Datasets
     ↓
SQLite Database
     ↓
SQL Analysis
     ↓
Tableau Public Dashboard
Important project stats

Tumhare actual project data ke according:

## 📈 Dataset

- 1,243 IPL match files
- 295,732 delivery records
- 19 seasons
- 738 players
- Delivery-level batting data
