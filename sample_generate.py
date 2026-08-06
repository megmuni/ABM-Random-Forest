# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 14:03:41 2026

@author: mm07

This file samples parameters to use as ABM input.

"""

import numpy as np
import pandas as pd

# --- Settings to edit -------------------------------------------------
INPUT_FILE = "parameters.xlsx"
SHEET_NAME = "Sheet1"
OUTPUT_FILE = "input_home.xlsx"
N_ITER = 5000        # Number of iterations for RF
NUM_PAR = 67          # Number of parameters
RNG_SEED = None        # Set an int here for reproducibility, or leave None
Z_95 = 1.96            # z-score used to convert [lower, upper] into a std dev
# -----------------------------------------------------------------------

rng = np.random.default_rng(RNG_SEED)

def sample_truncnorm(mean, sigma, lower, upper, size, rng):
    """
    Draw `size` samples from a normal(mean, sigma) distribution truncated
    to [lower, upper], so that bounds [a, b] are a hard min/max
    """
    a_std = (lower - mean) / sigma
    b_std = (upper - mean) / sigma
    return truncnorm.rvs(a_std, b_std, loc=mean, scale=sigma, size=size,
                          random_state=rng)

# --- Load parameter file ------------------------------------------------
# Columns:
#   'Mean'    -> default/mean value; used directly when Vary? is blank
#   'Lower'   -> lower bound (a) -- hard min
#   'Upper'   -> upper bound (b) -- hard max
#   'SD'      -> std dev, precomputed as (Upper - Lower) / 2
#   'Type'    -> distribution type: 1=lognormal, 2=discrete lognormal,
#                3=normal, 4=uniform
#   'Vary?'   -> blank=vary this parameter, 'N'=use Mean for every run

df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
df = df.iloc[:NUM_PAR].reset_index(drop=True)

samples = np.zeros((N_ITER, NUM_PAR))
stats = np.zeros((NUM_PAR, 5))  # [index, mean/log-mean, std/log-std, min, max]

for i in range(NUM_PAR):
    row = df.iloc[i]
    a = row["Lower"]
    b = row["Upper"]
    sd = row["SD"]
    dist_type = row["Type"]
    mean_val = row["Mean"]

    # blank -> vary; 'N' -> don't vary
    vary_raw = row["Vary?"]
    dont_vary = isinstance(vary_raw, str) and vary_raw.strip().upper() == "N"

    stats[i, 0] = i + 1

    # --- If not varying, just use the Mean value for every iteration ---
    if dont_vary:
        r = np.full(N_ITER, mean_val, dtype=float)
        samples[:, i] = r
        stats[i, 1] = mean_val
        stats[i, 2] = 0.0
        stats[i, 3] = r.min()
        stats[i, 4] = r.max()
        continue

    # --- Type 1: lognormal, truncated to [a, b] (hard bounds) ---
    if dist_type == 1:
        mu = np.log(mean_val)
        # SD column is on the linear scale (Upper - Lower)/2; convert to an
        # approximate log-scale sigma the same way (using log-bounds).
        sigma = (np.log(b) - np.log(a)) / 2
        log_r = sample_truncnorm(mu, sigma, np.log(a), np.log(b), N_ITER, rng)
        r = np.exp(log_r)
        samples[:, i] = r
        stats[i, 1] = np.mean(np.log(r))
        stats[i, 2] = np.std(np.log(r), ddof=1)

    # --- Type 2: discrete lognormal (same as Type 1, rounded to nearest 0.5) ---
    elif dist_type == 2:
        mu = np.log(mean_val)
        sigma = (np.log(b) - np.log(a)) / 2
        log_x = sample_truncnorm(mu, sigma, np.log(a), np.log(b), N_ITER, rng)
        x = np.exp(log_x)
        y = np.floor(x)
        frac = x - y
        r = np.where(frac >= 0.5, y + 0.5, y)
        r = np.clip(r, a, b)  # rounding-only edge safety net
        samples[:, i] = r
        stats[i, 1] = np.mean(np.log(r))
        stats[i, 2] = np.std(np.log(r), ddof=1)

    # --- Type 3: normal, truncated to [a, b] (hard bounds) ---
    elif dist_type == 3:
        r = sample_truncnorm(mean_val, sd, a, b, N_ITER, rng)
        samples[:, i] = r
        stats[i, 1] = np.mean(r)
        stats[i, 2] = np.std(r, ddof=1)

    # --- Type 4: uniform between lower and upper bound ---
    elif dist_type == 4:
        r = rng.uniform(a, b, N_ITER)
        samples[:, i] = r
        stats[i, 1] = np.mean(r)
        stats[i, 2] = np.std(r, ddof=1)

    else:
        raise ValueError(f"Unknown distribution type '{dist_type}' at parameter {i + 1}")

    stats[i, 3] = r.min()
    stats[i, 4] = r.max()

# --- Save sampled parameter matrix --------------------------------------
samples_df = pd.DataFrame(samples)
samples_df.to_excel(OUTPUT_FILE, sheet_name="Sheet1", index=False, header=False)

print(f"Done. Wrote {N_ITER} samples for {NUM_PAR} parameters to '{OUTPUT_FILE}'.")