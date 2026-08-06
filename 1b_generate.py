# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 14:54:46 2026

@author: mm07

Part 1B: This script generates individual config files to use as ABM input, 
based on the output from sample_generate.py (1A).

Takes the parameter matrix produced by 1A (input_home.xlsx) and, for each row
(i.e., one sampled parameter set) produces a full copy of the ABM's JSON config
template with only the parameters changed. All other config sections
(world init, chemistry, etc.) are copied through unchanged. 

"""

import pandas as pd
import re
from pathlib import Path

# --- Settings to edit -------------------------------------------------
template_file = "simulation_config.template.json"
samples_file = "input_home.xlsx"   # output of Part 1A: rows = iterations, cols = params, in order
output_dir = Path("samples")
bio_key_re = re.compile(r'^\s*"biology"\s*:')
# -----------------------------------------------------------------------

# Matches lines like:  "key": 12.34,   // anything at all (including N/A)
line_re = re.compile(
    r'^(?P<prefix>\s*"[^"]+"\s*:\s*)'
    r'(?P<value>-?\d+\.?\d*)'
    r'(?P<suffix>,?\s*//.*)$'
)

def load_template_lines(path):
    with open(path, "r") as f:
        return f.readlines()
    
def find_variable_line_indices(lines):
    """Only look at lines from the "biology" key onward (skips world_init
    and chemistry entirely). Within that region, vary any numeric field
    that has a trailing // comment, regardless of what the comment says."""
    idxs = []
    in_biology = False
    for i, line in enumerate(lines):
        if not in_biology:
            if bio_key_re.match(line):
                in_biology = True
            continue
        m = line_re.match(line)
        if m:
            idxs.append(i)
    return idxs

def write_sample_config(lines, var_idxs, values, out_path):
    new_lines = lines.copy()
    for idx, val in zip(var_idxs, values):
        m = line_re.match(new_lines[idx])
        prefix, suffix = m.group("prefix"), m.group("suffix") or ""
        val_str = str(int(val)) if float(val).is_integer() else f"{val:.6g}"
        new_lines[idx] = f"{prefix}{val_str}{suffix}\n"
    with open(out_path, "w") as f:
        f.writelines(new_lines)

def main():
    lines = load_template_lines(template_file)
    var_idxs = find_variable_line_indices(lines)
    print(f"Found {len(var_idxs)} //-tagged variable parameters under 'biology'.")

    samples_df = pd.read_excel(samples_file, header=None)
    n_iter, n_params = samples_df.shape

    if n_params != len(var_idxs):
        raise ValueError(
            f"Mismatch: samples file has {n_params} columns but template has "
            f"{len(var_idxs)} //-tagged parameters under 'biology'. Check that "
            f"Part 1A's parameter order/count matches the template's tagged-line order."
        )

    output_dir.mkdir(exist_ok=True)
    for num in range(n_iter):
        values = samples_df.iloc[num].values
        out_path = output_dir / f"sample{num + 1}.json"
        write_sample_config(lines, var_idxs, values, out_path)

    print(f"Wrote {n_iter} config files to '{output_dir}/'")
    
if __name__ == "__main__":
    main()
