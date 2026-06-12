# Teiko Bio - Immune Cell Population Analysis

A Python-based data pipeline and interactive dashboard for analyzing immune cell populations in clinical trial data, specifically examining how the drug candidate **miraclib** affects immune cell populations.

## Quick Start

```bash
# 1. Install dependencies
make setup

# 2. Run the full pipeline (loads data + generates analysis)
make pipeline

# 3. Launch the interactive dashboard
make dashboard
```

Then open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser.

## Project Structure

```
├── cell-count.csv          # Input data file
├── load_data.py            # Part 1: Database initialization and data loading
├── analysis.py             # Parts 2-4: Analysis pipeline
├── dashboard.py            # Interactive Dash/Plotly dashboard
├── requirements.txt        # Python dependencies
├── Makefile                # Build targets (setup, pipeline, dashboard)
├── output/                 # Generated analysis outputs
│   ├── part2_data_overview.csv
│   ├── part3_stats_results.csv
│   ├── part3_frequencies.csv
│   ├── part3_boxplot.png
│   └── part4_subset_analysis.csv
└── cell_counts.db          # SQLite database (generated)
```

## Database Schema

The relational schema normalizes the CSV into four tables:

### Tables

| Table | Description |
|-------|-------------|
| `projects` | Unique projects (prj1, prj2, prj3) |
| `subjects` | Patient metadata (condition, age, sex, treatment, response) |
| `samples` | Individual biological samples with timepoint info |
| `cell_counts` | Normalized cell counts (one row per sample per population) |

### Schema Diagram

```
projects (1) ──── (many) subjects (1) ──── (many) samples (1) ──── (many) cell_counts
   │                        │                        │                        │
   project_id (PK)          subject_id (PK)          sample_id (PK)           id (PK)
                            project_id (FK)          subject_id (FK)          sample_id (FK)
                            condition                sample_type              population
                            age                      time_from_treatment_     count
                            sex                        start
                            treatment
                            response
```

### Design Rationale

- **Normalization**: The flat CSV is decomposed into proper relational form to eliminate redundancy. Subject metadata is stored once per subject rather than repeated across every sample row.
- **Cell counts as rows**: Instead of 5 wide columns (b_cell, cd8_t_cell, etc.), counts are stored as key-value pairs in `cell_counts`. This makes it easy to add new populations without schema changes.
- **Scalability**: With indexes on commonly filtered columns (condition, treatment, response, sample_type, time), queries remain fast even with hundreds of thousands of samples across many projects. The normalized design means adding new projects or populations requires no schema migration.
- **Indexing strategy**: Indexes are created on columns frequently used in WHERE clauses and JOIN conditions (e.g., `project_id`, `condition`, `treatment`, `response`, `sample_type`, `time_from_treatment_start`, `population`). This ensures that analytical queries - which filter by disease type, treatment arm, response status, or timepoint - execute efficiently via index scans rather than full table scans, even as data grows to hundreds of thousands of rows.
- **Analytics flexibility**: The row-based cell count structure supports GROUP BY and pivot operations naturally, making it straightforward to compute relative frequencies, compare populations, and filter subsets.

## Analysis Parts

### Part 1: Data Management
- Creates SQLite database with relational schema
- Loads all 10,500 rows from `cell-count.csv`
- Script: `load_data.py`

### Part 2: Initial Analysis - Data Overview
- Computes relative frequency (percentage) of each cell population per sample
- Outputs a summary table with columns: sample, total_count, population, count, percentage
- **Rationale**: Relative frequencies (percentages) are used instead of raw counts because total cell counts vary between samples. Normalizing to percentages allows fair comparison across samples with different total cell yields.

### Part 3: Statistical Analysis
- Filters: melanoma patients, miraclib treatment, PBMC samples only
- Compares responders vs non-responders
- Generates boxplot visualization
- Performs Mann-Whitney U test for statistical significance
- **Rationale**: The Mann-Whitney U test was chosen because it is a non-parametric test that does not assume normality in the data - biological cell frequency distributions are often skewed. It compares two independent groups (responders vs non-responders) and is robust to outliers and unequal sample sizes. PBMC samples are used exclusively because whole blood (WB) has different cell composition characteristics and mixing sample types would introduce confounding variation. Boxplots provide a clear visual of distributional differences between the two groups.

### Part 4: Data Subset Analysis
- Filters: melanoma, PBMC, baseline (time=0), miraclib
- Reports: samples per project, responders/non-responders count, male/female count
- **Rationale**: Baseline (time=0) samples are selected to examine pre-treatment immune status before drug effects confound the measurements. Filtering to melanoma + miraclib isolates the specific disease-drug combination of interest. Reporting project, response, and sex breakdowns provides demographic context needed to assess whether the cohort is balanced or if any observed effects might be driven by confounders.
- **Base filter design**: A shared `base_filter` string is defined once and reused across all Part 4 queries. This ensures consistency - every sub-question (project counts, response counts, sex counts) operates on the exact same subset of data. It also makes maintenance easier: if filter criteria change, only one place needs updating rather than duplicating the WHERE clause in multiple queries, reducing the risk of subtle bugs from mismatched filters.

## Dashboard

The interactive dashboard ([http://127.0.0.1:8050](http://127.0.0.1:8050)) provides:

- **Tab 1**: Data Overview with bar charts and filterable/sortable data table
- **Tab 2**: Statistical comparison with interactive boxplots and Mann-Whitney U results
- **Tab 3**: Subset analysis with pie charts and bar charts for demographics

## Dependencies

- Python 3.6+
- pandas, scipy, matplotlib, plotly, dash
- SQLite (bundled with Python)

## Instructions to Reproduce

1. Clone this repository
2. Ensure Python 3.6+ is installed
3. Run `make setup` to install dependencies
4. Run `make pipeline` to execute the full analysis
5. Run `make dashboard` to start the interactive dashboard
6. Open http://127.0.0.1:8050 in a browser
