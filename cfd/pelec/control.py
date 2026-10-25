"""Small explicit SI -> native cgs contract for the first integration gate."""
import math
import re

CASE = dict(temperature_K=1800., pressure_Pa=377916.972, phi=1.176,
            final_time_s=2e-7, cells=[8, 8], extent_m=[0.001, 0.001])

def validate(case):
    if set(case) != set(CASE):
        raise ValueError('Unexpected or missing case fields')
    for name in ('temperature_K','pressure_Pa','phi','final_time_s'):
        value = case[name]
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid '+name)
    if not 300 <= case['temperature_K'] <= 2500 or case['final_time_s'] > 1e-6:
        raise ValueError('Outside bounded P1 reactor scope')
    if case['cells'] != [8,8] or case['extent_m'] != [0.001,0.001]:
        raise ValueError('P1 requires the declared uniform 8x8 periodic domain')

def inputs(case, dt, reacting=True):
    validate(case)
    if not math.isfinite(dt) or not 0 < dt <= case['final_time_s']/10:
        raise ValueError('Invalid control timestep')
    text = f'''# Uniform methane/oxygen; native cgs units; NOT an engine case.
stop_time = {case['final_time_s']:.17g}
max_step = 10000
geometry.is_periodic = 1 1
geometry.coord_sys = 0
geometry.prob_lo = 0 0
geometry.prob_hi = {case['extent_m'][0]*100:.17g} {case['extent_m'][1]*100:.17g}
amr.n_cell = 8 8
pelec.lo_bc = Interior Interior
pelec.hi_bc = Interior Interior
pelec.do_react = {int(reacting)}
pelec.do_hydro = 1
pelec.diffuse_temp = 0
pelec.diffuse_enth = 0
pelec.diffuse_spec = 0
pelec.diffuse_vel = 0
pelec.sdc_iters = 2
pelec.chem_integrator = ReactorCvode
cvode.solve_type = GMRES
cvode.max_order = 5
ode.rtol = 1e-11
ode.atol = 1e-22
pelec.fixed_dt = {dt:.17g}
pelec.init_shrink = 1
pelec.cfl = 0.2
pelec.dt_cutoff = 1e-20
pelec.sum_interval = 1
pelec.v = 1
amr.v = 1
amr.max_level = 0
amr.blocking_factor = 8
amr.max_grid_size = 8
amr.checkpoint_files_output = 0
amr.plot_files_output = 1
amr.plot_file = plt
amr.plot_int = 1000000
amr.plot_per = {case['final_time_s']/4:.17g}
amr.derive_plot_vars = pressure
pelec.plot_massfrac = 1
pelec.plot_rhoy = 0
amr.data_log = datlog
prob.p_init = {case['pressure_Pa']*10:.17g}
prob.T_init = {case['temperature_K']:.17g}
prob.phi = {case['phi']:.17g}
amrex.signal_handling = 0
amrex.abort_on_unused_inputs = 1
'''
    if not reacting:
        text = '\n'.join(line for line in text.splitlines() if not line.startswith(
            ('pelec.chem_integrator', 'cvode.', 'ode.'))) + '\n'
    return text

def log_errors(text):
    # Native CVODE failures can be printed without a failing process exit.
    pattern = r'CVODE ERROR|CVode.*failed|SUNDIALS_ERROR|AMReX::Abort|SIGSEGV|SIGABRT|\bERROR\b|turning on reactions while using ReactorNull'
    return [line for line in text.splitlines() if re.search(pattern, line, re.I)]

def plot_time(path):
    lines = (path/'Header').read_text().splitlines()
    n = int(lines[1])
    if int(lines[n+2]) != 2:
        raise ValueError('Expected a native 2D plotfile')
    t = float(lines[n+3])
    if not math.isfinite(t) or t < 0:
        raise ValueError('Invalid native plot time')
    return t
