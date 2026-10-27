#ifndef PROB_PARM_H
#define PROB_PARM_H
#include <AMReX_REAL.H>
#include <AMReX_GpuMemory.H>
struct ProbParmDevice {
  int mode=0, feed=0, seed=0, pairs=72, netl_startup=0;
  amrex::Real exit_p=1.e6, seed_angle=0.03490658503988659;
  amrex::Real p0=3779169.7229, T0=300, Tprod=1500, height=0.38;
  amrex::Real seed_p=1.e8, seed_T=4000, seed_u=2.e5, seed_length=3., seed_theta=1.5707963267948966;
  amrex::Real plenum_fuel=13994000., plenum_oxygen=13095000., plenum_T=300.;
  amrex::Real fuel_radius=0.03935, oxygen_radius=0.06225, jet_angle=0.5235987755982988, impingement_height=0.216;
  amrex::GpuArray<amrex::Real,NUM_SPECIES> Y{}, Yprod{}, Yseed{};
  int nx=0; amrex::Real dx=0; amrex::Real* conserved=nullptr;
};
struct ProbParmHost { amrex::Gpu::DeviceVector<amrex::Real> conserved; };
#endif
