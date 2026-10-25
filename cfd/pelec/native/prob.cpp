// Initialization adapter only. Upstream PeleC evolves all flow/species/energy.
#include "prob.H"
#include <cmath>
void pc_prob_close() {}
extern "C" {
void amrex_probinit(const int*, const int*, const int*, const amrex::Real*, const amrex::Real*) {
  auto& p = *PeleC::h_prob_parm_device;
  amrex::ParmParse pp("prob");
  amrex::Real phi;
  pp.get("p_init", p.p_init); // native cgs: dyn/cm^2
  pp.get("T_init", p.T_init);
  pp.get("phi", phi);
  if (!std::isfinite(phi) || phi <= 0. || !std::isfinite(p.p_init) || p.p_init <= 0. ||
      !std::isfinite(p.T_init) || p.T_init < 300. || p.T_init > 2500.) {
    amrex::Abort("Methane2D: invalid initialization or outside P1 temperature scope");
  }
  amrex::Real x[NUM_SPECIES] = {0.};
  x[CH4_ID] = phi / (phi + 2.);
  x[O2_ID] = 2. / (phi + 2.);
  CKXTY(x, p.massfrac.data());
  auto eos = pele::physics::PhysicsType::eos();
  eos.PYT2RE(p.p_init, p.massfrac.data(), p.T_init, p.rho_init, p.e_init);
}
}
void PeleC::problem_post_timestep() {}
void PeleC::problem_post_init() {}
void PeleC::problem_post_restart() {}
