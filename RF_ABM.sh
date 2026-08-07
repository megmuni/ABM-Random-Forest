#!/bin/bash
#SBATCH --account=def-nicoleli
#SBATCH --time=7-00:00:00
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:2
#SBATCH --nodes=1
#SBATCH --mem=64000M
#SBATCH --mail-user=grace.yu@mail.mcgill.ca
#SBATCH --mail-type=ALL

module load cuda

export OMP_NUM_THREADS=32
export OMP_NESTED=TRUE

for ((c=1; c<=5400; c++))
do
    cp ./samples/sample${c} ./sample.txt
    ./bin/testRun --numticks 145 --inputfile configFiles/config_Scaffold_GH10.txt --wxw 0.6 --wyw 0.6 --wzw 0.6
    cp ./output/Output_Biomarkers.csv ./output/output_home/output_${c}.csv
done

# Finish the script
exit 0
