"""Bind one MPI local rank to one visible GPU before AMReX initializes CUDA."""
import os,sys
rank=int(os.environ.get('OMPI_COMM_WORLD_LOCAL_RANK','0'))
visible=os.environ.get('CUDA_VISIBLE_DEVICES','0,1,2,3').split(',')
if rank>=len(visible):raise RuntimeError('MPI local rank exceeds allocated GPU count')
os.environ['CUDA_VISIBLE_DEVICES']=visible[rank]
print(f'GPU_BINDING local_rank={rank} visible_device={visible[rank]}',flush=True)
os.execv(sys.argv[1],sys.argv[1:])
