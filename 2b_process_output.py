# -*- coding: utf-8 -*-
"""
Created on Tue Aug 11 16:32:38 2026

@author: mm07

This script post-processes ABM simulation data in preparation for Random Forest 
sensitivity analysis.

Combines the previous MATLAB scripts output_process.m and input_process.m



"""

import numpy as np
import pandas as pd
from pathlib import Path

# --- Settings to edit -------------------------------------------------
n_samples = 10
output_dir = Path("output_home")     # where output_<N>.csv files live
input_home_file = "input_home.xlsx"          # produced by Part 1A
filtered_input_file = "input_home_filtered.xlsx"
bad_samples_log = "bad_samples.txt"

timepoint_rows = { # row indices for different timepoints
    "day0": 1 - 1,
    "day1": 49 - 1,
    "day2": 97 - 1,
    "day3": 145 - 1,
    # Uncomment / add more as needed
    # "day5": 241 - 1,
    # "day7": 337 - 1,
    # "day14": 673 - 1,
    # "day28": 1345 - 1,
}

# optional: also filter by file byte size if you know the minimum size 
# of a "good" output file
min_file_size_bytes = None

# -----------------------------------------------------------------------

def check_sample(num):
    """
    Check whether sample `num`'s output CSV is "good".
    Returns (is_good: bool, reason: str or None, data: np.ndarray or None)
    """
    filepath = output_dir / f"output_{num}.csv"
 
    if not filepath.exists():
        return False, "missing file", None
 
    if min_file_size_bytes is not None and filepath.stat().st_size < min_file_size_bytes:
        return False, f"file too small (<{min_file_size_bytes} bytes)", None
 
    # read CSV as a plain numeric matrix
    # if file can't be parsed as numeric
    # data at all, throw an error and treat it as a bad run
    try:
        data = pd.read_csv(filepath, header=None).to_numpy(dtype=float)
    except Exception as e:
        return False, f"failed to read/parse ({e})", None
 
    if np.isnan(data).any():
        return False, "contains NaN", None
 
    if np.isinf(data).any():
        return False, "contains Inf", None
 
    return True, None, data

def main():
    # collect rows for each timepoint, keyed by sample number so results
    # from different timepoints stay aligned to the same set of good samples
    timepoint_rows = {tp: [] for tp in timepoint_rows}
    good_sample_numbers = []
    bad_samples = []  # list of (sample_num, reason) tuples, for logging
 
    for num in range(1, n_samples + 1):
        is_good, reason, data = check_sample(num)
 
        if not is_good:
            bad_samples.append((num, reason))
            continue
 
        # verify output file has enough rows for every requested
        # timepoint before pulling from it
        max_row_needed = max(timepoint_rows.values())
        if data.shape[0] <= max_row_needed:
            bad_samples.append((num, f"too few rows ({data.shape[0]}, needed >{max_row_needed})"))
            continue
 
        good_sample_numbers.append(num)
        for tp, row_idx in timepoint_rows.items():
            timepoint_rows[tp].append(data[row_idx, :])
 
    # save each timepoint's collected rows to its own excel file
    for tp, rows in timepoint_rows.items():
        df = pd.DataFrame(rows)
        # add the original sample number as the first column, so each
        # row can always be traced back to its source sample
        df.insert(0, "sample_num", good_sample_numbers)
        out_path = f"{tp}.xlsx"
        df.to_excel(out_path, sheet_name="Sheet1", index=False, header=False)
        print(f"Wrote {len(rows)} good rows to '{out_path}'.")
 
    # filter input_home.xlsx to only the good samples
    input_df = pd.read_excel(input_home_file, header=None)
    good_row_positions = [n - 1 for n in good_sample_numbers]
    filtered_input_df = input_df.iloc[good_row_positions].reset_index(drop=True)
 
    # tag the sample number here, so input rows can be cross-referenced
    # against the output timepoint files by sample_num
    filtered_input_df.insert(0, "sample_num", good_sample_numbers)
    filtered_input_df.to_excel(filtered_input_file, sheet_name="Sheet1", index=False, header=False)
    print(f"Wrote {len(good_sample_numbers)} good input rows to '{filtered_input_file}'.")
 
    # log which samples were excluded and why
    with open(bad_samples_log, "w") as f:
        f.write(f"{len(bad_samples)} of {n_samples} samples excluded:\n")
        for num, reason in bad_samples:
            f.write(f"  sample {num}: {reason}\n")
    print(f"{len(bad_samples)} bad samples logged to '{bad_samples_log}'.")
    print(f"{len(good_sample_numbers)} good samples out of {n_samples} total.")

if __name__ == "__main__":
    main()