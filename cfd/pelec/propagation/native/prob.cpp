// Initial conserved profile only. All evolution uses unmodified upstream code.
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
 auto& d=PeleC::prob_parm_host->conserved;d.resize(v.size());
 amrex::Gpu::copy(amrex::Gpu::hostToDevice,v.begin(),v.end(),d.begin());p.conserved=d.data();
}
}
void PeleC::problem_post_timestep(){}
void PeleC::problem_post_init(){}
void PeleC::problem_post_restart(){}
