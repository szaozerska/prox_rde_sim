// Initialization of an independent conserved-cell-average profile only.
// Evolution remains entirely in pinned PeleC/PelePhysics.
#include "prob.H"
#include <cmath>
#include <fstream>
void pc_prob_close() {}
extern "C" {
void amrex_probinit(const int*, const int*, const int*, const amrex::Real*, const amrex::Real*) {
  auto& p=*PeleC::h_prob_parm_device;
  amrex::ParmParse pp("prob");std::string filename;pp.get("profile",filename);
  std::ifstream input(filename);int columns=0;
  if (!(input >> p.nx >> columns >> p.dx) || p.nx<8 || p.nx>2048 ||
      columns!=NUM_SPECIES+3 || !std::isfinite(p.dx) || p.dx<=0.)
    amrex::Abort("FormedWave: invalid profile header");
  amrex::Vector<amrex::Real> values(p.nx*columns);
  for (auto& value:values) {
    if (!(input >> value) || !std::isfinite(value))
      amrex::Abort("FormedWave: incomplete/nonfinite conserved profile");
  }
  std::string extra;if (input >> extra) amrex::Abort("FormedWave: trailing profile data");
  for (int i=0;i<p.nx;++i) {
    const auto* row=values.data()+i*columns;
    if (row[0]<=0.) amrex::Abort("FormedWave: nonpositive density");
    amrex::Real sum=0.;
    for(int n=0;n<NUM_SPECIES;++n) {
      if(row[n+3]<0.) amrex::Abort("FormedWave: negative species");
      sum+=row[n+3];
    }
    if(std::abs(sum/row[0]-1.)>1.e-10) amrex::Abort("FormedWave: species sum mismatch");
  }
  auto& device=PeleC::prob_parm_host->conserved;device.resize(values.size());
  amrex::Gpu::copy(amrex::Gpu::hostToDevice,values.begin(),values.end(),device.begin());
  p.conserved=device.data();
}
}
void PeleC::problem_post_timestep() {}
void PeleC::problem_post_init() {}
void PeleC::problem_post_restart() {}
