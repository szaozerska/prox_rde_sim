#ifndef PROB_PARM_H
#define PROB_PARM_H
#include <AMReX_REAL.H>
#include <AMReX_GpuMemory.H>
struct ProbParmDevice {
 int nx=0;amrex::Real dx=0.,fill=0.,p0=0.,T0=0.,area=0.,pback=0.,R=0.,gamma=0.;
 amrex::Real bg_rho=0.,bg_e=0.,bg_T=0.;
 amrex::GpuArray<amrex::Real,NUM_SPECIES> freshY={0.},bgY={0.};
 int uniform_control=0;
 amrex::Real species_floor=-1.e-12;
 amrex::GpuArray<amrex::Real,NUM_SPECIES*NUM_ELEMENTS> element_weights={0.};
 amrex::GpuArray<amrex::Real,NUM_ELEMENTS> elements={0.};
 amrex::Real* conserved=nullptr;
};
struct ProbParmHost {amrex::Gpu::DeviceVector<amrex::Real> conserved;};
#endif
