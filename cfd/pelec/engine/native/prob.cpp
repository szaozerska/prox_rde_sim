// Problem initializer, approximate engine boundaries, and state assertions.
// All native evolution/chemistry/thermodynamics source remains unmodified.
#include "prob.H"
#include <cmath>
#include <fstream>
void pc_prob_close(){}
extern "C" {
void amrex_probinit(const int*,const int*,const int*,const amrex::Real*,const amrex::Real*){
 auto& p=*PeleC::h_prob_parm_device;amrex::ParmParse pp("prob");std::string file;pp.get("profile",file);
 std::ifstream f(file);int cols=0;
 if(!(f>>p.nx>>cols>>p.dx)||p.nx<8||p.nx>8192||cols!=NUM_SPECIES+3||!std::isfinite(p.dx)||p.dx<=0.)amrex::Abort("Invalid profile header");
 amrex::Vector<amrex::Real> v(p.nx*cols);
 for(auto& x:v)if(!(f>>x)||!std::isfinite(x))amrex::Abort("Incomplete/nonfinite profile");
 std::string extra;if(f>>extra)amrex::Abort("Trailing profile data");
 for(int i=0;i<p.nx;++i){auto* r=v.data()+i*cols;if(r[0]<=0.)amrex::Abort("Invalid density");amrex::Real sum=0.;
  for(int n=3;n<cols;++n){if(r[n]<0.)amrex::Abort("Negative species");sum+=r[n];}
  if(std::abs(sum/r[0]-1.)>1.e-10)amrex::Abort("Species sum error");}
 pp.query("uniform_control",p.uniform_control);
 pp.query("species_floor",p.species_floor);
 if(p.species_floor < -1.e-8 || p.species_floor > -1.e-12)amrex::Abort("Invalid trace budget");
 amrex::Vector<amrex::Real> ew,ee;pp.getarr("element_weights",ew);pp.getarr("elements",ee);
 if(ew.size()!=NUM_SPECIES*NUM_ELEMENTS||ee.size()!=NUM_ELEMENTS)amrex::Abort("Element coefficient dimensions");
 for(int n=0;n<NUM_SPECIES*NUM_ELEMENTS;++n)p.element_weights[n]=ew[n];
 for(int n=0;n<NUM_ELEMENTS;++n)p.elements[n]=ee[n];
 pp.get("fill",p.fill);pp.get("p0",p.p0);pp.get("T0",p.T0);pp.get("area",p.area);pp.get("pback",p.pback);pp.get("R",p.R);pp.get("gamma",p.gamma);pp.get("bg_T",p.bg_T);
 amrex::Vector<amrex::Real> fresh,bg;pp.getarr("freshY",fresh);pp.getarr("bgY",bg);
 if(fresh.size()!=NUM_SPECIES||bg.size()!=NUM_SPECIES)amrex::Abort("Wrong inlet species count");
 amrex::Real sy=0.,by=0.;
 for(int n=0;n<NUM_SPECIES;++n){if(!std::isfinite(fresh[n])||!std::isfinite(bg[n])||fresh[n]<0.||bg[n]<0.)amrex::Abort("Invalid boundary species");p.freshY[n]=fresh[n];p.bgY[n]=bg[n];sy+=fresh[n];by+=bg[n];}
 if(std::abs(sy-1.)>1.e-10||std::abs(by-1.)>1.e-10)amrex::Abort("Boundary species sum");
 if(p.fill<=0||p.p0<=0||p.T0<200||p.T0>5000||p.area<=0||p.area>1||p.pback<=0||p.R<=0||p.gamma<=1||p.bg_T<200||p.bg_T>5000)amrex::Abort("Invalid engine parameters");
 auto eos=pele::physics::PhysicsType::eos();eos.PYT2RE(p.pback,p.bgY.data(),p.bg_T,p.bg_rho,p.bg_e);
 auto& d=PeleC::prob_parm_host->conserved;d.resize(v.size());
 amrex::Gpu::copy(amrex::Gpu::hostToDevice,v.begin(),v.end(),d.begin());p.conserved=d.data();
}
}
void validate_engine_state(amrex::MultiFab& state,const ProbParmDevice p){
 for(amrex::MFIter mfi(state);mfi.isValid();++mfi){
  const auto a=state.const_array(mfi);
  amrex::ParallelFor(mfi.validbox(),[=] AMREX_GPU_DEVICE(int i,int j,int k) noexcept {
   const auto rho=a(i,j,k,URHO),T=a(i,j,k,UTEMP);
   engine_require(std::isfinite(rho)&&rho>0.&&std::isfinite(T)&&T>=200.&&T<=5000.,"Engine state outside density/thermo validity");
   amrex::Real Y[NUM_SPECIES],sum=0.;
   for(int n=0;n<NUM_SPECIES;++n){Y[n]=a(i,j,k,UFS+n)/rho;sum+=Y[n];if(!std::isfinite(Y[n])||Y[n]<p.species_floor||Y[n]>1.+1.e-10)printf("Invalid species: i=%d j=%d n=%d Y=%.17e T=%.17e\n",i,j,n,Y[n],T);engine_require(std::isfinite(Y[n])&&Y[n]>=p.species_floor&&Y[n]<=1.+1.e-10,"Engine species bounds");}
   engine_require(std::abs(sum-1.)<1.e-9,"Engine species sum");
   for(int e=0;e<NUM_ELEMENTS;++e){amrex::Real value=0.;for(int n=0;n<NUM_SPECIES;++n)value+=Y[n]*p.element_weights[n*NUM_ELEMENTS+e];engine_require(std::abs(value-p.elements[e])<1.e-7,"Engine local element consistency");}
   auto eos=pele::physics::PhysicsType::eos();amrex::Real pressure;eos.RTY2P(rho,T,Y,pressure);
   engine_require(std::isfinite(pressure)&&pressure>0.,"Engine pressure bounds");
  });
 }
 amrex::Gpu::streamSynchronize();
}
void PeleC::problem_post_timestep(){validate_engine_state(get_new_data(State_Type),*PeleC::h_prob_parm_device);}
void PeleC::problem_post_init(){problem_post_timestep();}
void PeleC::problem_post_restart(){problem_post_timestep();}
