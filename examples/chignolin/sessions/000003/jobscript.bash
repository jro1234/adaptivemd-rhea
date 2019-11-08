#!/bin/bash
# Job submitted with command:
# sbatch  -t 40 -e /autofs/nccs-svm1_proj/bif112/adaptivemd-rhea/examples/chignolin/sessions/000003/admd.err -o /autofs/nccs-svm1_proj/bif112/adaptivemd-rhea/examples/chignolin/sessions/000003/admd.out -J admd -p gpu -A bif112 -N 1 sessions/000003/jobscript.bash
# 1- Load the AdaptiveMD environment
source /ccs/home/jrossyra/admd-rhea.bashrc
export ADMD_SAVELOGS="True"
echo "CUDA compiler: $(which nvcc)"
export ADMD_DBURL="mongodb://172.30.144.4:33234/"
echo "new ADMD_DBURL: $ADMD_DBURL"
# 2- Update job state to running
cd /autofs/nccs-svm1_proj/bif112/adaptivemd-rhea/examples/chignolin/sessions/000003
echo "RUNNING" > admd.job.state
# 3- Shell Job 1, Start AdaptiveMD to coordinate AdaptiveMD Event
adaptivemdruntime chignolin --n_traj 0 --rescue_only 1> admd.adaptivemd.out 2> admd.adaptivemd.err & EVENT_PID=$!
# 4- Shell Job 2, Launch AdaptiveMDWorkers
srun -n 1 --cpus-per-task 14 --verbose startworker chignolin $ADMD_DBURL 1 4 SLURM_PROCID 2> admd.workers.launch.err 1> admd.workers.launch.out & WORKERS_APID=$! 
# 5- Shut down Shell Jobs after AdaptiveMD Event (shell job 2) terminates
wait "$EVENT_PID"
wait "%1"
echo "STOPPING" > admd.job.state
kill "%2"
sleep "3"
echo "COMPLETE" > admd.job.state
# 6- Help the LRMS with explicit job kill
echo "scancel $SLURM_JOB_ID"
scancel "$SLURM_JOB_ID"