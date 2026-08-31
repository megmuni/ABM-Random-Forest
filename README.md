# ABM-Random-Forest
Contains the Random Forest sensitivity analysis workflow for VUA Lab biomaterial ABMs

## Overview
This workflow follows the same overall steps as the Random Forest (RF) sensitivity analysis procedure described in [Garg et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6675024/). The previous workflow can be found at [https://github.com/VF-ABM/RF-SPOTPY](https://github.com/VF-ABM/RF-SPOTPY).

Random Forest (RF) is a machine learning algorithm that optimizes weighted trees from input parameters. The algorithm takes a set of weighted trees and computes a GINI index for each parameter that was used in the trees, as an indicator of its significance to the ABM. In sensitivity analysis, we try to determine which parameters are most important to the ABM; in other words, we want to compute the GINI indices of all of the ABM parameters and rank them.

## Step 1: Generate randomly sampled parameter sets as ABM input
### Part 1A: Sample parameters to use as ABM input (`1a_sample_generate.py`)
The following settings can be edited:
| Variable    | Default             | Description                                                                                                                                            |
|-------------|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| input_file  | `"parameters.xlsx"` | Input file listing all parameters, default/mean values, SD, lower and upper bounds, type of distribution to sample from, and whether or not to vary it |
| sheet_name  | `"Sheet1"`          |                                                                                                                                                        |
| output_file | `"input_home.xlsx"` | Output file for matrix of sampled parameters                                                                                                           |
| n_iter      | `10`                | Number of iterations for RF                                                                                                                            |
| n_par       | `67`                | Number of parameters                                                                                                                                   |
| rng_seed    | `None`              | Set an int here for reproducibility, or leave None                                                                                                     |


### Part 1B: Turn sampled parameters into config files to use as ABM input (`1b_generate.py`)
The output from 1A (`input_home.xlsx`) is used as input for this script. It outputs a directory called `samples`, which contains `n_iter` config files following the structure of `simulation_config.template.json`.

## Step 2: Generate data with the ABM, using the sampled paramaters, for RF to learn from
### Part 2A: Running the model on the cluster
1. If your sampled parameters (the folder "samples") are not in the ABM-Random-Forest repo by default, manually upload them to the cluster
   using the [Globus file manager](https://globus.alliancecan.ca).
1. Edit the `SBATCH` settings and other variables in the settings block to align with your file paths and names
1. Run RF_ABM.sh (`sbatch RF_ABM.sh`). The script will copy executables over from your ABM directory, submit simulation jobs (in batches)
   for each of the sampled parameter sets, and collect the output.
1. Download the ABM outputs (`/output/output_home/`).

### Part 2B: Preparing the output data (`2b_process_output.py`)
The following settings can be edited:
| Variable            | Default                      | Description                                                                                                                                            |
|---------------------|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| n_samples           | `10`                         | Number of RF runs that were executed (matches n_iter in Part 1A)                                                                                       |
| output_dir          | `"Output_home"`              | Where the output_<N>.csv files live (from the ABM in Part 2A)                                                                                          |
| input_home_file     | `"input_home.xlsx"`          | Produced by Part 1A                                                                                                                                    |
| filtered_input_file | `"input_home_filtered.xlsx"` | Will create a new (filtered) input_home file if necessary, if there are bad runs that need to be excluded from RF                                      |
| bad_samples_log     | `"bad_samples.txt"`          | Number of parameters                                                                                                                                   |
| TIMEPOINT_ROWS      |                              | Row indices for different timepoints                                                                                                                   |

## Step 3: Perform RF sensitivity analysis (`3_randomforest.py`)
1. The following settings can be edited:
| Variable    | Default             | Description                                                                                                                               |
|-------------|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| random_seed | `1`                 | Random seed for reproducibility                                                                                                           |
| n_trees     | `500`               | Number of trees to use in Random Forest (n should be large enough to converge, but will take longer for very large n)                     |
| input_file  | `"input_home.xlsx"` | Cleaned/filtered input file                                                                                                               |
| output_file | `"day3.xlsx"`       | output file for the timepoint to run RF on                                                                                                |
| model_type  | `"classification"`  | Model type can be regression or classification - classification treats every value of Y as its own category (equivalent to factor() in R) |
1. Choose which output you want to run RF on (e.g., collagen, cell type, etc.) For example, if you select `day3.xlsx` in `output_file` and run RF for collagen in `main()`, the results are giving you the significance of each parameter to the amount of collagen in the model at Day 3.
1. The script produces a variable importance plot, ranking each of the parameters' significance with respect to your biomarker of choice, based on mean decrease in impurity in the Random Forest.

