# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 13:04:19 2026

@author: mmunip

Random Forest sensitivity analysis for the ABM. 

For each biomarker of interest, fits a Random Forest relating the sampled
input parameters (X) to that outcome (Y) at a given timepoint.

"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

# --- Settings to edit -------------------------------------------------
random_seed = 1
n_trees = 500
input_file = "input_home_filtered.xlsx" # cleaned/filtered input file
output_file = "day3.xlsx" # output file for the timepoint to run RF on
model_type = "classification" 

# -----------------------------------------------------------------------

np.random.seed(random_seed)

def load_and_clean_inputs(path):
    """
    Load the input parameter matrix and drop any zero-variance columns
    (parameters that never varied, e.g. those marked "don't vary" upstream,
    or that happened to sample a constant value).
 
    Returns:
        X_clean   -- DataFrame of only the varying parameters
        X_raw     -- DataFrame of all parameters, unfiltered
        kept_cols -- original column numbers that were kept (for labeling)
    """
    X_raw = pd.read_excel(path, header=None)
 
    variances = X_raw.var(axis=0, skipna=True)
    nonzero_var_mask = variances > 0
 
    kept_cols = X_raw.columns[nonzero_var_mask]
    removed_cols = X_raw.columns[~nonzero_var_mask]
 
    X_clean = X_raw.loc[:, nonzero_var_mask]
 
    # 1-indexed labels (matching R's paste("X", kept_indices) convention),
    # used to name columns / label importance plots.
    kept_labels = [f"X{c + 1}" for c in kept_cols]
 
    print(f"Kept {len(kept_cols)} of {X_raw.shape[1]} parameters "
          f"(dropped {len(removed_cols)} zero-variance columns: "
          f"{[c + 1 for c in removed_cols]})")
 
    X_clean = X_clean.copy()
    X_clean.columns = kept_labels
 
    return X_clean, X_raw, kept_labels

def plot_correlation_heatmap(X_clean, out_path="correlation_heatmap.png"):
    """
    Produces a correlation matrix, reordered so that similarly-correlated 
    parameters are grouped together (via hierarchical clustering), 
    and rendered as a heatmap.
    """
    corr = X_clean.corr()
 
    # Hierarchical clustering on the correlation matrix to determine a
    # reordering of columns
    link = linkage(corr, method="average")
    dendro = dendrogram(link, no_plot=True, labels=corr.columns.tolist())
    ordered_cols = dendro["ivl"]
    corr_reordered = corr.loc[ordered_cols, ordered_cols]
 
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_reordered, cmap="RdBu_r", center=0, square=True,
                xticklabels=True, yticklabels=True)
    plt.title("Parameter correlation matrix (hierarchically clustered)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved correlation heatmap to '{out_path}'.")

def run_rf(X, Y, y_name, model_type=model_type,
                                n_trees=n_trees, seed=random_seed):
    """
    Fits a Random Forest relating parameters X to outcome Y, prints/returns
    variable importances, and saves a horizontal bar chart of them.
    """
    if model_type == "classification":
        model = RandomForestClassifier(n_estimators=n_trees, random_state=seed)
        Y_fit = Y.astype("category").cat.codes
    else:
        model = RandomForestRegressor(n_estimators=n_trees, random_state=seed)
        Y_fit = Y
 
    model.fit(X, Y_fit)
 
    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=False)
 
    print(f"\nVariable importance for {y_name}:")
    print(importances)
 
    # Plot, most important at the top
    plt.figure(figsize=(8, max(4, 0.25 * len(importances))))
    importances.sort_values().plot(kind="barh")
    plt.xlabel("Mean decrease in impurity")
    plt.title(f"Variable importance: {y_name}")
    plt.tight_layout()
    out_path = f"varimp_{y_name}.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved variable importance plot to '{out_path}'.")
 
    return model, importances

def main():
    # --- Load and clean inputs -------------------------------------------
    X_clean, X_raw, kept_labels = load_and_clean_inputs(input_file)
 
    # --- Correlation plot on cleaned data ---------------------------------
    plot_correlation_heatmap(X_clean)
 
    # --- Load outputs -------------------------------------------------------
    output = pd.read_excel(output_file, header=None)
 
    # --- Collagen (column 6) --------------------------------------
    Y_coll = output.iloc[:, 5]
    run_rf(X_clean, Y_coll, "collagen")
 
    # --- TGF-B (column 5) -----------------------------------------
    Y_tgf = output.iloc[:, 4]
    run_rf(X_clean, Y_tgf, "TGF-B")
 
    # --- % Differentiation (column 20) ----------------------------
    Y_diff = output.iloc[:, 19]
    run_rf(X_clean, Y_diff, "pct_differentiation")
 
 
if __name__ == "__main__":
    main()
    