#ifndef PROB_PARM_H
#define PROB_PARM_H
#include <AMReX_REAL.H>
#include <AMReX_GpuMemory.H>
struct ProbParmDevice {
  int nx=0;
  amrex::Real dx=0.;
  amrex::Real* conserved=nullptr;
};
struct ProbParmHost { amrex::Gpu::DeviceVector<amrex::Real> conserved; };
#endif
