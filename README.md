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
