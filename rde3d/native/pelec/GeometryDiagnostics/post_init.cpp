// Read-only geometry diagnostics from the actual PeleC flux-boundary structures.
// Injected into the upstream Sod case's empty problem_post_init hook.
void
PeleC::problem_post_init()
{
  if (!eb_in_domain || level != 0 || amrex::ParallelDescriptor::NProcs() != 1) {
    amrex::Abort("Geometry diagnostics require one process, level zero, and EB");
  }
  const auto dx = geom.CellSizeArray();
  const auto lo = geom.ProbLoArray();
  std::ofstream surface("native_surface.csv");
  surface << std::setprecision(17);
  surface << "i,j,k,x_cm,y_cm,z_cm,nx,ny,nz,area_cm2,vfrac\n";
  for (amrex::MFIter mfi(vfrac, false); mfi.isValid(); ++mfi) {
    const auto& device = sv_eb_bndry_geom[mfi.LocalIndex()];
    amrex::Gpu::HostVector<EBBndryGeom> host(device.size());
    amrex::Gpu::copy(amrex::Gpu::deviceToHost, device.begin(), device.end(), host.begin());
    for (const auto& b : host) {
      // Sparse native structures contain ghost cells: count only owned cells.
      if (!mfi.validbox().contains(b.iv)) { continue; }
      surface << b.iv[0] << ',' << b.iv[1] << ',' << b.iv[2];
      for (int d = 0; d < 3; ++d) {
        surface << ',' << lo[d] + (b.iv[d] + .5 + b.eb_centroid[d]) * dx[d];
      }
      for (int d = 0; d < 3; ++d) { surface << ',' << b.eb_normal[d]; }
      surface << ',' << b.eb_area * dx[0] * dx[1] << ',' << b.eb_vfrac << '\n';
    }
  }
  const auto& factory = dynamic_cast<const amrex::EBFArrayBoxFactory&>(Factory());
  auto aperture = factory.getAreaFrac()[2]->ToMultiFab(1., 0.);
  amrex::Real inlet = 0., outlet = 0.;
  const int bottom = geom.Domain().smallEnd(2);
  const int top = geom.Domain().bigEnd(2) + 1;
  for (amrex::MFIter mfi(aperture, false); mfi.isValid(); ++mfi) {
    const auto& source = aperture[mfi];
    amrex::FArrayBox host(source.box(), 1, amrex::The_Pinned_Arena());
    amrex::Gpu::copy(amrex::Gpu::deviceToHost, source.dataPtr(),
                     source.dataPtr() + source.size(), host.dataPtr());
    const auto a = host.const_array();
    for (amrex::BoxIterator it(mfi.validbox()); it.ok(); ++it) {
      const auto& iv = it();
      if (iv[2] == bottom) { inlet += a(iv) * dx[0] * dx[1]; }
      if (iv[2] == top) { outlet += a(iv) * dx[0] * dx[1]; }
    }
  }
  std::ofstream ports("native_ports.json");
  ports << std::setprecision(17) << "{\"inlet_cm2\":" << inlet
        << ",\"outlet_cm2\":" << outlet << "}\n";
}
