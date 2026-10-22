// Case initialization only; evolved fields and chemistry use upstream PeleC.
// Adapted from the pinned PeleC Exec/RegTests/zeroD/prob.cpp (BSD-3-Clause).
#include "prob.H"
#include <cmath>

void pc_prob_close() {}

extern "C" {
void amrex_probinit(const int*, const int*, const int*, const amrex::Real*, const amrex::Real*)
{
  auto& p = *PeleC::h_prob_parm_device;
  amrex::ParmParse pp("prob");
  pp.get("p_init", p.p_init); // PeleC cgs: dyn/cm^2, not Pa
  pp.get("T_init", p.T_init);
  amrex::Vector<amrex::Real> y;
  pp.getarr("mass_fractions", y);
  if (y.size() != NUM_SPECIES || !std::isfinite(p.p_init) || p.p_init <= 0. ||
      !std::isfinite(p.T_init) || p.T_init < 300. || p.T_init > 5000.) {
    amrex::Abort("MethaneZeroD: invalid pressure, temperature or species count");
  }
  amrex::Real sum = 0.;
  for (int n = 0; n < NUM_SPECIES; ++n) {
    if (!std::isfinite(y[n]) || y[n] < 0.) {
      amrex::Abort("MethaneZeroD: nonfinite or negative mass fraction");
    }
    p.massfrac[n] = y[n];
    sum += y[n];
  }
  if (std::abs(sum - 1.) > 1.e-12) {
    amrex::Abort("MethaneZeroD: mass fractions must sum to one; no silent normalization");
  }
  auto eos = pele::physics::PhysicsType::eos();
  eos.PYT2RE(p.p_init, p.massfrac.begin(), p.T_init, p.rho_init, p.e_init);
}
}
void PeleC::problem_post_timestep() {}
void PeleC::problem_post_init() {}
void PeleC::problem_post_restart() {}
