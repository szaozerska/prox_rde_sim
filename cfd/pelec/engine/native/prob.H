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
// Release CUDA builds compile assert() away. This guard is unconditional.
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void engine_require(bool condition,const char* message){
 if(condition)return;
#ifdef AMREX_USE_CUDA
 printf("Engine validation failed: %s\n",message);
 __trap();
#else
 amrex::Abort(message);
#endif
}
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void pc_initdata(int i,int j,int k,amrex::Array4<amrex::Real> const& s,
 amrex::GeometryData const& geom,ProbParmDevice const& p){
 engine_require(i>=0&&i<p.nx,"Profile index");
 engine_require(amrex::Math::abs(geom.CellSize(0)/p.dx-1.)<1.e-12,"Profile spacing");
 const auto* r=p.conserved+i*(NUM_SPECIES+3);
 const auto ylo=geom.ProbLo(1)+j*geom.CellSize(1);
 const auto weight=amrex::max(0.,amrex::min(1.,(p.fill-ylo)/geom.CellSize(1)));
 const auto w=p.uniform_control?0.:weight;
 const auto rho=w*r[0]+(1-w)*p.bg_rho;
 const auto mom=w*r[1];const auto energy=w*r[2]+(1-w)*p.bg_rho*p.bg_e;
 const auto e=energy/rho-.5*(mom/rho)*(mom/rho);amrex::Real Y[NUM_SPECIES];
 for(int n=0;n<NUM_SPECIES;++n){s(i,j,k,UFS+n)=w*r[3+n]+(1-w)*p.bg_rho*p.bgY[n];Y[n]=s(i,j,k,UFS+n)/rho;}
 amrex::Real T=1000.;auto eos=pele::physics::PhysicsType::eos();eos.REY2T(rho,e,Y,T);
 engine_require(T>=200.&&T<=5000.,"Initializer/boundary temperature range");
 s(i,j,k,URHO)=rho;s(i,j,k,UMX)=mom;s(i,j,k,UMY)=0.;s(i,j,k,UMZ)=0.;
 s(i,j,k,UEDEN)=energy;s(i,j,k,UEINT)=rho*e;s(i,j,k,UTEMP)=T;
}
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void bcnormal(const amrex::Real*,const amrex::Real* si,amrex::Real* se,int idir,int sgn,
 amrex::Real,amrex::GeometryData const&,ProbParmDevice const& p,const amrex::GpuArray<amrex::Real,AMREX_SPACEDIM>&){
 for(int n=0;n<NVAR;++n)se[n]=si[n];
 if(idir!=1)return;
 auto eos=pele::physics::PhysicsType::eos();amrex::Real Y[NUM_SPECIES],pressure,cs;
 for(int n=0;n<NUM_SPECIES;++n)Y[n]=si[UFS+n]/si[URHO];
 eos.RTY2P(si[URHO],si[UTEMP],Y,pressure);eos.RTY2Cs(si[URHO],si[UTEMP],Y,cs);
 amrex::Real T=si[UTEMP],u=si[UMX]/si[URHO],v=si[UMY]/si[URHO],pb=pressure;
 if(sgn==1){
  // Homogenized premixed converging-injector law; zero flow during blockage.
  if(pressure>=p.p0){se[UMY]=-si[UMY];return;}
  const auto g=p.gamma;const auto crit=std::pow(2./(g+1.),g/(g-1.));
  const auto ratio=amrex::max(crit,pressure/p.p0);
  const auto flux=p.area*p.p0/std::sqrt(p.R*p.T0)*std::sqrt(2*g/(g-1.)*(std::pow(ratio,2/g)-std::pow(ratio,(g+1)/g)));
  // Pressure-matched bulk inflow. Recover total enthalpy with native EOS;
  // mass flux is area averaged, not a resolved sonic jet velocity.
  for(int n=0;n<NUM_SPECIES;++n)Y[n]=p.freshY[n];u=0.;
  amrex::Real h0;CKHBMS(p.T0,Y,h0);amrex::Real lo=200.,hi=p.T0;
  for(int it=0;it<40;++it){T=.5*(lo+hi);amrex::Real rho,e,h;eos.PYT2RE(pressure,Y,T,rho,e);v=flux/rho;CKHBMS(T,Y,h);
   if(h+.5*v*v>h0)hi=T;else lo=T;}
  T=.5*(lo+hi);amrex::Real rho,e,h;eos.PYT2RE(pressure,Y,T,rho,e);v=flux/rho;CKHBMS(T,Y,h);
  engine_require(std::abs(h+.5*v*v-h0)<1.e-6*amrex::max(std::abs(h0),1.),"Inlet enthalpy bracket failed");
 }else{
  // Locally frozen-gamma outgoing characteristic with prescribed back pressure.
  if(v>=cs)return;
  amrex::Real cp,cv;eos.TY2Cp(T,Y,cp);eos.TY2Cv(T,Y,cv);const auto g=cp/cv;
  pb=p.pback;T*=std::pow(pb/pressure,(g-1.)/g);
  engine_require(T>=200.&&T<=5000.,"Initializer/boundary temperature range");amrex::Real rho,e,ce;eos.PYT2RE(pb,Y,T,rho,e);eos.RTY2Cs(rho,T,Y,ce);
  v+=2*(cs-ce)/(g-1.);
  if(v<0.){T=p.bg_T;u=0.;for(int n=0;n<NUM_SPECIES;++n)Y[n]=p.bgY[n];}
 }
 amrex::Real rho,e;eos.PYT2RE(pb,Y,T,rho,e);
 se[URHO]=rho;se[UMX]=rho*u;se[UMY]=rho*v;se[UMZ]=0.;se[UEINT]=rho*e;se[UEDEN]=rho*(e+.5*(u*u+v*v));se[UTEMP]=T;
 for(int n=0;n<NUM_SPECIES;++n)se[UFS+n]=rho*Y[n];
}
void pc_prob_close();
using ProblemSpecificFunctions=DefaultProblemSpecificFunctions;
#endif
