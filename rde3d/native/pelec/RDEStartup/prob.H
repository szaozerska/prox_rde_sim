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
AMREX_GPU_HOST_DEVICE AMREX_FORCE_INLINE
void make_state(amrex::Real* s, amrex::Real pressure, amrex::Real temperature,
                const amrex::Real* y, amrex::Real ux=0, amrex::Real uy=0, amrex::Real uz=0) {
  auto eos=pele::physics::PhysicsType::eos(); amrex::Real rho,e;
  eos.PYT2RE(pressure,y,temperature,rho,e);
  for(int n=0;n<NVAR;++n)s[n]=0;
  s[URHO]=rho;s[UMX]=rho*ux;s[UMY]=rho*uy;s[UMZ]=rho*uz;
  s[UEINT]=rho*e;s[UEDEN]=rho*(e+0.5*(ux*ux+uy*uy+uz*uz));s[UTEMP]=temperature;
  for(int n=0;n<NUM_SPECIES;++n)s[UFS+n]=rho*y[n];
}
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void pc_initdata(int i,int j,int k,amrex::Array4<amrex::Real> const& a,
                amrex::GeometryData const& g,ProbParmDevice const& p) {
  amrex::Real s[NVAR]={0};
  if(p.mode==1) {
    const auto* row=p.conserved+i*(NUM_SPECIES+3);auto rho=row[0],u=row[1]/rho,e=row[2]/rho-.5*u*u;
    amrex::Real y[NUM_SPECIES],T=1000;
    for(int n=0;n<NUM_SPECIES;++n)y[n]=row[n+3]/rho;
    auto eos=pele::physics::PhysicsType::eos();eos.REY2T(rho,e,y,T);
    s[URHO]=rho;s[UMX]=row[1];s[UEINT]=rho*e;s[UEDEN]=row[2];s[UTEMP]=T;
    for(int n=0;n<NUM_SPECIES;++n)s[UFS+n]=row[n+3];
  } else {
    auto x=g.ProbLo(0)+(i+.5)*g.CellSize(0),y=g.ProbLo(1)+(j+.5)*g.CellSize(1),z=g.ProbLo(2)+(k+.5)*g.CellSize(2);
    auto r=std::sqrt(x*x+y*y);auto theta=std::atan2(y,x);
    make_state(s,p.p0,p.T0,p.Y.data());
    if(p.mode==2 && z>p.height) {
      // NETL: fresh mixture in the first 5 mm; air beyond with an axial pressure taper.
      auto pressure=p.netl_startup ? p.p0+(p.exit_p-p.p0)*(z-p.height)/(g.ProbHi(2)-p.height) : p.p0;
      make_state(s,pressure,p.Tprod,p.Yprod.data());
    }
    auto behind=p.seed_theta-theta;
    if(behind<0)behind+=2*3.141592653589793;
    if(p.mode==2 && p.seed && r>0 && (p.netl_startup ? behind<p.seed_angle : behind*r<p.seed_length) && z<p.height) {
      // NETL variant uses a finite angular sector and zero imposed velocity.
      // Initial gas composition in that hot sector is an explicit input assumption.
      make_state(s,p.seed_p,p.seed_T,p.Yseed.data(),-p.seed_u*y/r,p.seed_u*x/r,0);
    }
  }
  for(int n=0;n<NVAR;++n)a(i,j,k,n)=s[n];
}
AMREX_GPU_DEVICE AMREX_FORCE_INLINE
void bcnormal(const amrex::Real* x,const amrex::Real* si,amrex::Real* se,
              int idir,int sgn,amrex::Real,amrex::GeometryData const&,ProbParmDevice const& p,
              const amrex::GpuArray<amrex::Real,AMREX_SPACEDIM>&) {
  for(int n=0;n<NVAR;++n)se[n]=si[n];
  if(idir!=2 || sgn!=1)return;
  // Closed portions of the base reflect axial momentum; no mass is admitted.
  se[UMZ]=-si[UMZ];
  if(!p.feed)return;
  auto r=std::sqrt(x[0]*x[0]+x[1]*x[1]);if(r<3.31 || r>3.81)return;
  amrex::Real Y[NUM_SPECIES]={0},ppl=0,ut=0; bool opening=false;
  if(p.feed==1) {
    for(int n=0;n<NUM_SPECIES;++n)Y[n]=p.Y[n];ppl=1.35e7;opening=true;
  } else {
    // Two inclined mouths per pair in the radial plane, aimed to meet at
    // the stated height. Tangential startup is separate from steady injection.
    auto theta=std::atan2(x[1],x[0]);auto period=2*3.141592653589793/p.pairs;
    auto phase=theta-period*std::floor(theta/period+.5);
    auto arc=3.56*phase,offset=p.impingement_height*std::tan(p.jet_angle);
    auto dr=r-3.56;
    auto ca=std::cos(p.jet_angle);
    bool fuel=(dr+offset)*(dr+offset)*ca*ca+arc*arc<p.fuel_radius*p.fuel_radius;
    bool oxygen=(dr-offset)*(dr-offset)*ca*ca+arc*arc<p.oxygen_radius*p.oxygen_radius;
    if(fuel){Y[CH4_ID]=1;ppl=p.plenum_fuel;ut=1;opening=true;}
    if(oxygen){Y[O2_ID]=1;ppl=p.plenum_oxygen;ut=-1;opening=true;}
  }
  if(!opening)return;
  auto eos=pele::physics::PhysicsType::eos();amrex::Real yi[NUM_SPECIES],pressure;
  for(int n=0;n<NUM_SPECIES;++n)yi[n]=si[UFS+n]/si[URHO];
  eos.RTY2P(si[URHO],si[UTEMP],yi,pressure);
  if(pressure>=ppl)return;
  // Reservoir-fed converging-port approximation; the native Riemann flux
  // determines actual supply. No prescribed mass-flow claim is made.
  amrex::Real rho,e,cp,cv;
  eos.PYT2RE(ppl,Y,p.plenum_T,rho,e);eos.TY2Cp(p.plenum_T,Y,cp);eos.TY2Cv(p.plenum_T,Y,cv);
  auto gamma=cp/cv,R=cp-cv;
  auto ratio=amrex::max(pressure/ppl,std::pow(2/(gamma+1),gamma/(gamma-1)));
  auto T=p.plenum_T*std::pow(ratio,(gamma-1)/gamma);
  auto speed=std::sqrt(amrex::max(amrex::Real(0),2*cp*(p.plenum_T-T)));
  auto radial=ut*speed*std::sin(p.jet_angle);
  make_state(se,ppl*ratio,T,Y,radial*x[0]/r,radial*x[1]/r,speed*(p.feed==2?std::cos(p.jet_angle):1));
}
void pc_prob_close();
using ProblemSpecificFunctions=DefaultProblemSpecificFunctions;
#endif
