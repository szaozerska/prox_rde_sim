#ifndef PROB_H
#define PROB_H
#include <AMReX_ParmParse.H>
#include <AMReX_Geometry.H>
#include <AMReX_FArrayBox.H>
#include "mechanism.H"
#include "PeleC.H"
#include "IndexDefines.H"
#include "PelePhysics.H"
#include "Tagging.H"
#include "ProblemSpecificFunctions.H"
#include "prob_parm.H"
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void pc_initdata(int i,int j,int k,amrex::Array4<amrex::Real> const& s,
                 amrex::GeometryData const& geom,ProbParmDevice const& p) {
  AMREX_ALWAYS_ASSERT(i>=0 && i<p.nx);
  AMREX_ALWAYS_ASSERT(amrex::Math::abs(geom.CellSize(0)/p.dx-1.)<1.e-12);
  const auto* r=p.conserved+i*(NUM_SPECIES+3);
  const auto rho=r[0]; const auto u=r[1]/rho; const auto e=r[2]/rho-.5*u*u;
  amrex::Real Y[NUM_SPECIES];
  for(int n=0;n<NUM_SPECIES;++n){Y[n]=r[n+3]/rho;s(i,j,k,UFS+n)=r[n+3];}
  amrex::Real T=1000.; auto eos=pele::physics::PhysicsType::eos();eos.REY2T(rho,e,Y,T);
  AMREX_ALWAYS_ASSERT(T>=199.9 && T<=5000.);
  s(i,j,k,URHO)=rho;s(i,j,k,UMX)=r[1];s(i,j,k,UMY)=0.;s(i,j,k,UMZ)=0.;
  s(i,j,k,UEDEN)=r[2];s(i,j,k,UEINT)=rho*e;s(i,j,k,UTEMP)=T;
}
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void bcnormal(const amrex::Real*,const amrex::Real*,amrex::Real*,const int,const int,
 const amrex::Real,amrex::GeometryData const&,ProbParmDevice const&,
 const amrex::GpuArray<amrex::Real,AMREX_SPACEDIM>&){}
void pc_prob_close();
using ProblemSpecificFunctions=DefaultProblemSpecificFunctions;
#endif
