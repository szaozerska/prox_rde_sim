#include "prob.H"
#include <fstream>
void pc_prob_close() {}
extern "C" void amrex_probinit(const int*,const int*,const int*,const amrex::Real*,const amrex::Real*) {
  auto& p=*PeleC::h_prob_parm_device;amrex::ParmParse pp("prob");
  pp.get("mode",p.mode);pp.query("feed",p.feed);pp.query("seed",p.seed);
  pp.query("p0",p.p0);pp.query("T0",p.T0);pp.query("Tprod",p.Tprod);pp.query("height",p.height);
  pp.query("seed_p",p.seed_p);pp.query("seed_T",p.seed_T);pp.query("seed_u",p.seed_u);pp.query("seed_length",p.seed_length);
  pp.query("fuel_radius",p.fuel_radius);pp.query("oxygen_radius",p.oxygen_radius);
  amrex::Vector<amrex::Real> y,yp,ys;pp.getarr("Y",y);pp.getarr("Yprod",yp);ys=yp;if(pp.contains("Yseed"))pp.getarr("Yseed",ys);
  if(y.size()!=NUM_SPECIES || yp.size()!=NUM_SPECIES || ys.size()!=NUM_SPECIES)amrex::Abort("Species count mismatch");
  for(int n=0;n<NUM_SPECIES;++n){p.Y[n]=y[n];p.Yprod[n]=yp[n];p.Yseed[n]=ys[n];}
  for(auto const& values:{y,yp,ys}) {amrex::Real sum=0;for(auto v:values){if(!std::isfinite(v)||v<0)amrex::Abort("Invalid composition");sum+=v;}if(std::abs(sum-1)>1e-10)amrex::Abort("Composition sum");}
  if(p.mode<0 || p.mode>2 || p.feed<0 || p.feed>2 || p.p0<=0 || p.T0<200 || p.T0>5000)amrex::Abort("Invalid prototype inputs");
  if(p.mode==1) {
    std::string file;pp.get("profile",file);std::ifstream in(file);int cols;
    if(!(in>>p.nx>>cols>>p.dx)||cols!=NUM_SPECIES+3||p.nx<8||p.nx>4096)amrex::Abort("Invalid profile");
    amrex::Vector<amrex::Real> a(p.nx*cols);for(auto& v:a)if(!(in>>v)||!std::isfinite(v))amrex::Abort("Invalid profile data");
    auto& d=PeleC::prob_parm_host->conserved;d.resize(a.size());amrex::Gpu::copy(amrex::Gpu::hostToDevice,a.begin(),a.end(),d.begin());p.conserved=d.data();
  }
}
void PeleC::problem_post_timestep() {}
void PeleC::problem_post_init() {}
void PeleC::problem_post_restart() {}
