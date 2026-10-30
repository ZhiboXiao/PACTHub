"""Reference-free runtime for the unchanged V3 CUDA projector and solver updates."""
import hashlib
import json
from pathlib import Path
import time
import torch
from .operator import norm_value, tv_gradient, tv_adjoint


def load_projector(device):
    from torch.utils.cpp_extension import load
    source = Path(__file__).with_name('torch_disk_projector_cuda.cu')
    # A content-based name invalidates the cache when the vendored kernel changes.
    name = 'pa_mb_v3_' + hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    major, minor = torch.cuda.get_device_capability(device)
    return load(name=name, sources=[str(source)], extra_cuda_cflags=[
        '-O3', f'-gencode=arch=compute_{major}{minor},code=sm_{major}{minor}'], verbose=False)


def solve(operator, measured, options, *, verbose=True):
    """V3 fixed-iteration primal/dual updates; restore the input normalization.

    Power iterations estimate the spectral scale (not a certified upper bound).
    History evaluates each UPDATED iterate, including the zero initialization.
    """
    started = time.perf_counter()
    data_norm = norm_value(measured)
    if not 0 < data_norm < float('inf'):
        raise ValueError('MB input has zero or nonfinite L2 norm')
    data = measured / data_norm
    rhs = operator.adjoint(data)
    rhs_norm = norm_value(rhs); rhs_peak = float(rhs.max().item())
    if not 0 < rhs_norm < float('inf') or not 0 < rhs_peak < float('inf'):
        raise ValueError('Invalid/nonpositive MB adjoint; check geometry, polarity and time support')
    power = rhs / rhs_norm
    estimates = []
    for i in range(options.power_iterations):
        value = operator.adjoint(operator.forward(power))
        estimate = norm_value(value)
        if not 0 < estimate < float('inf'):
            raise ValueError('Invalid spectral estimate')
        estimates.append(estimate); power = value / estimate
        if verbose: print(f'MB spectral iteration {i+1}: {estimate:.8g}', flush=True)
    del power, value
    largest = estimates[-1]
    l2 = options.l2_relative * largest
    l1 = options.l1_relative * rhs_peak
    tv = options.tv_relative * rhs_peak
    tau = .70 / (largest + l2)
    sigma = .80 * (1 / tau - largest / 2) / 12
    x = torch.zeros_like(rhs); extrapolated = torch.zeros_like(rhs)
    dual = [torch.zeros_like(rhs) for _ in range(3)]
    prediction = torch.zeros_like(data)
    history = [dict(iteration=0, relative_rf_residual=1., objective=.5, active_fraction=0.)]
    for iteration in range(1, options.iterations + 1):
        tick = time.perf_counter()
        gradient = tv_gradient(extrapolated)
        for p, g in zip(dual, gradient): p.add_(g, alpha=sigma)
        if tv == 0:
            for p in dual: p.zero_()
        else:
            divisor = torch.clamp(torch.sqrt(sum(p*p for p in dual)) / tv, min=1.)
            for p in dual: p.div_(divisor)
        data_gradient = -rhs if iteration == 1 else operator.adjoint(prediction - data)
        new = torch.clamp(x - tau * (data_gradient + tv_adjoint(*dual)) - tau*l1, min=0) / (1 + tau*l2)
        previous_norm = norm_value(x)
        change = norm_value(new-x) / previous_norm if previous_norm > 0 else None
        extrapolated = 2*new - x; x = new
        prediction = operator.forward(x)
        residual = norm_value(prediction-data)
        grad = tv_gradient(x)
        tv_value = float(torch.sqrt(sum(g*g for g in grad)).sum().item())
        objective = .5*residual**2 + l1*float(x.sum().item()) + tv*tv_value + .5*l2*float((x*x).sum().item())
        if not 0 <= objective < float('inf'):
            raise RuntimeError('Nonfinite MB iterate')
        row = dict(iteration=iteration, relative_rf_residual=residual, objective=objective,
            relative_change=change, active_fraction=float(torch.count_nonzero(x).item())/x.numel(),
            seconds=time.perf_counter()-tick)
        history.append(row)
        if verbose: print(f'MB iteration {iteration}: RF residual {residual:.6f}; objective {objective:.8g}', flush=True)
    summary = dict(history=history, input_l2_norm=data_norm, output_multiplier=data_norm,
        amplitude_units='preprocessed_RF_and_operator_dependent; not_calibrated_pressure',
        spectral_estimates=estimates, lambda_l1=l1, lambda_tv=tv, lambda_l2=l2,
        primal_step=tau, dual_step=sigma, rhs_norm=rhs_norm, rhs_positive_peak=rhs_peak,
        stop_reason='requested_fixed_iterations', convergence_claim=False,
        rf_residual_scope='fitted_measurements_not_independent_quality_or_physical_accuracy',
        normalization='L2 input normalization reversed in exported volume', solver_seconds=time.perf_counter()-started)
    return x*data_norm, summary
