"""
analysis.py - Parts 2, 3, and 4: Data Analysis

Part 2: Initial Analysis - Data Overview
Part 3: Statistical Analysis
Part 4: Data Subset Analysis

Usage:
    python analysis.py
"""

import sqlite3
import os

try:
    from scipy import stats as scipy_stats
except ImportError:
    print("ERROR: scipy is not installed. Please run 'make setup' or 'pip install scipy' first.")
    exit(1)

DB_PATH = "cell_counts.db"
OUTPUT_DIR = "output"


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# Part 2: Initial Analysis - Data Overview
# =============================================================================

def part2_data_overview(conn):
    """
    Generate a summary table of the relative frequency of each cell population.
    
    For each sample:
    - Calculate total cell count
    - Compute relative frequency (percentage) of each population
    
    Output columns: sample, total_count, population, count, percentage
    """
    print("\n" + "=" * 70)
    print("PART 2: Initial Analysis - Data Overview")
    print("=" * 70)

    cursor = conn.cursor()

    query = """
        SELECT 
            cc.sample_id AS sample,
            s_totals.total_count,
            cc.population,
            cc.count,
            ROUND(cc.count * 100.0 / s_totals.total_count, 2) AS percentage
        FROM cell_counts cc
        JOIN (
            SELECT sample_id, SUM(count) AS total_count
            FROM cell_counts
            GROUP BY sample_id
        ) s_totals ON cc.sample_id = s_totals.sample_id
        ORDER BY cc.sample_id, cc.population
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Write to CSV
    output_path = os.path.join(OUTPUT_DIR, "part2_data_overview.csv")
    with open(output_path, "w") as f:
        f.write("sample,total_count,population,count,percentage\n")
        for row in rows:
            f.write(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]}\n")

    print(f"  Output written to: {output_path}")
    print(f"  Total rows: {len(rows)}")

    # Print first few rows as preview
    print("\n  Preview (first 10 rows):")
    print(f"  {'sample':<14} {'total_count':>11} {'population':<12} {'count':>7} {'percentage':>10}")
    print(f"  {'-'*14} {'-'*11} {'-'*12} {'-'*7} {'-'*10}")
    for row in rows[:10]:
        print(f"  {row[0]:<14} {row[1]:>11} {row[2]:<12} {row[3]:>7} {row[4]:>9}%")


# =============================================================================
# Part 3: Statistical Analysis
# =============================================================================

def part3_statistical_analysis(conn):
    """
    Compare cell population relative frequencies between responders and 
    non-responders among melanoma patients receiving miraclib (PBMC only).
    
    - Boxplot visualization
    - Statistical significance testing (Mann-Whitney U test)
    """
    print("\n" + "=" * 70)
    print("PART 3: Statistical Analysis")
    print("=" * 70)

    cursor = conn.cursor()

    # Query: Get relative frequencies for melanoma + miraclib + PBMC patients
    query = """
        SELECT 
            sub.response,
            cc.population,
            cc.count * 100.0 / s_totals.total_count AS percentage
        FROM cell_counts cc
        JOIN samples sa ON cc.sample_id = sa.sample_id
        JOIN subjects sub ON sa.subject_id = sub.subject_id
        JOIN (
            SELECT sample_id, SUM(count) AS total_count
            FROM cell_counts
            GROUP BY sample_id
        ) s_totals ON cc.sample_id = s_totals.sample_id
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND sa.sample_type = 'PBMC'
          AND sub.response IN ('yes', 'no')
        ORDER BY cc.population, sub.response
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Organize data by population and response
    from collections import defaultdict
    data = defaultdict(lambda: {"yes": [], "no": []})

    for row in rows:
        response = row[0]
        population = row[1]
        percentage = row[2]
        data[population][response].append(percentage)

    # Statistical test (Mann-Whitney U)
    populations = sorted(data.keys())

    print("\n  Mann-Whitney U Test Results (Responders vs Non-Responders):")
    print(f"  {'Population':<12} {'U-statistic':>12} {'p-value':>12} {'Significant':>12}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    stats_results = []

    for pop in populations:
        responders = data[pop]["yes"]
        non_responders = data[pop]["no"]

        if len(responders) > 0 and len(non_responders) > 0:
            u_stat, p_value = scipy_stats.mannwhitneyu(
                responders, non_responders, alternative='two-sided'
            )
            significant = "Yes" if p_value < 0.05 else "No"
            stats_results.append({
                "population": pop,
                "u_statistic": u_stat,
                "p_value": p_value,
                "significant": significant,
                "n_responders": len(responders),
                "n_non_responders": len(non_responders)
            })
            print(f"  {pop:<12} {u_stat:>12.1f} {p_value:>12.6f} {significant:>12}")

    # Write stats results
    output_path = os.path.join(OUTPUT_DIR, "part3_stats_results.csv")
    with open(output_path, "w") as f:
        f.write("population,u_statistic,p_value,significant,n_responders,n_non_responders\n")
        for r in stats_results:
            f.write(f"{r['population']},{r['u_statistic']:.1f},{r['p_value']:.6f},{r['significant']},{r['n_responders']},{r['n_non_responders']}\n")
    print(f"\n  Stats results written to: {output_path}")

    # Generate boxplot
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(populations), figsize=(16, 6), sharey=False)
    if len(populations) == 1:
        axes = [axes]

    for i, pop in enumerate(populations):
        responders = data[pop]["yes"]
        non_responders = data[pop]["no"]

        bp = axes[i].boxplot(
            [non_responders, responders],
            labels=["Non-Responders", "Responders"],
            patch_artist=True
        )
        bp['boxes'][0].set_facecolor('#FF6B6B')
        bp['boxes'][1].set_facecolor('#4ECDC4')

        axes[i].set_title(pop.replace("_", " ").title())
        axes[i].set_ylabel("Relative Frequency (%)")
        axes[i].tick_params(axis='x', rotation=15)

    plt.suptitle(
        "Cell Population Relative Frequencies:\nResponders vs Non-Responders\n"
        "(Melanoma, Miraclib, PBMC)",
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout()

    plot_path = os.path.join(OUTPUT_DIR, "part3_boxplot.png")
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Boxplot saved to: {plot_path}")

    # Write raw data for boxplot
    output_path = os.path.join(OUTPUT_DIR, "part3_frequencies.csv")
    with open(output_path, "w") as f:
        f.write("population,response,percentage\n")
        for pop in populations:
            for resp in ["yes", "no"]:
                for pct in data[pop][resp]:
                    f.write(f"{pop},{resp},{pct:.4f}\n")
    print(f"  Frequency data written to: {output_path}")


# =============================================================================
# Part 4: Data Subset Analysis
# =============================================================================

def part4_subset_analysis(conn):
    """
    Filter melanoma PBMC samples at baseline (time=0) treated with miraclib.
    
    Report:
    1. How many samples from each project
    2. How many subjects were responders/non-responders
    3. How many subjects were males/females
    """
    print("\n" + "=" * 70)
    print("PART 4: Data Subset Analysis")
    print("=" * 70)

    cursor = conn.cursor()

    # Base query: melanoma + PBMC + baseline + miraclib
    base_filter = """
        FROM samples sa
        JOIN subjects sub ON sa.subject_id = sub.subject_id
        WHERE sub.condition = 'melanoma'
          AND sa.sample_type = 'PBMC'
          AND sa.time_from_treatment_start = 0
          AND sub.treatment = 'miraclib'
    """

    # 1. Identify all matching samples
    query_samples = f"SELECT sa.sample_id, sub.subject_id, sub.project_id {base_filter}"
    cursor.execute(query_samples)
    samples = cursor.fetchall()
    print(f"\n  Total matching samples: {len(samples)}")

    # 2. 1. Samples from each project
    query_projects = f"""
        SELECT sub.project_id, COUNT(sa.sample_id) AS sample_count
        {base_filter}
        GROUP BY sub.project_id
        ORDER BY sub.project_id
    """
    cursor.execute(query_projects)
    project_counts = cursor.fetchall()

    print("\n  1. Samples from each project:")
    for row in project_counts:
        print(f"     {row[0]}: {row[1]} samples")

    # 2. 2. Responders vs non-responders (count unique subjects)
    query_response = f"""
        SELECT sub.response, COUNT(DISTINCT sub.subject_id) AS subject_count
        {base_filter}
        AND sub.response IS NOT NULL
        GROUP BY sub.response
    """
    cursor.execute(query_response)
    response_counts = cursor.fetchall()

    print("\n  2. Subjects by response:")
    for row in response_counts:
        label = "Responders" if row[0] == "yes" else "Non-Responders"
        print(f"     {label}: {row[1]} subjects")

    # 2. 3. Males vs females (count unique subjects)
    query_sex = f"""
        SELECT sub.sex, COUNT(DISTINCT sub.subject_id) AS subject_count
        {base_filter}
        GROUP BY sub.sex
    """
    cursor.execute(query_sex)
    sex_counts = cursor.fetchall()

    print("\n  3. Subjects by sex:")
    for row in sex_counts:
        label = "Male" if row[0] == "M" else "Female"
        print(f"     {label}: {row[1]} subjects")

    # Write subset analysis output
    output_path = os.path.join(OUTPUT_DIR, "part4_subset_analysis.csv")
    with open(output_path, "w") as f:
        f.write("category,group,count\n")
        for row in project_counts:
            f.write(f"project,{row[0]},{row[1]}\n")
        for row in response_counts:
            label = "responders" if row[0] == "yes" else "non_responders"
            f.write(f"response,{label},{row[1]}\n")
        for row in sex_counts:
            label = "male" if row[0] == "M" else "female"
            f.write(f"sex,{label},{row[1]}\n")

    print(f"\n  Subset analysis written to: {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    """Run all analysis parts."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database '{DB_PATH}' not found. Run load_data.py first.")
        return

    ensure_output_dir()
    conn = get_connection()

    try:
        part2_data_overview(conn)
        part3_statistical_analysis(conn)
        part4_subset_analysis(conn)
    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("All analyses complete. Output files are in the 'output/' directory.")
    print("=" * 70)


if __name__ == "__main__":
    main()
