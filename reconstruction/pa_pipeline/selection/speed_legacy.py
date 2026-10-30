"""MF sound-speed candidate selection: standalone NumPy API, no project files.

Dependencies: numpy, scipy, scikit-image. CPU only; no MATLAB/CUDA/learned model.
All scientific scoring functions are unchanged from the retained MF algorithms.

Usage (no file I/O):
    from mf_sound_speed_portable import select_sound_speed
    result, audit = select_sound_speed(mips, speeds, x_mm, y_mm, wavelength_nm=800)

Inputs:
    mips: complete quantitative XY-MIPs [21, Ny, Nx], rows Y / columns X.
    speeds: [1490, 1491, ..., 1510] in m/s.
    x_mm, y_mm: uniformly increasing physical axes in millimetres.
    wavelength_nm: 690, 800 or 1064; controls review priority, not the scores.
    The same PA frames, geometry, preprocessing and projection depth must be
    used for all speeds. Do not use PNG montages or black-masked surface MIPs.

Outputs:
    result["methods"]["full_global_normalized_gradient"]["candidate"]
    result["methods"]["morphology_v2"]["candidate"]
    audit: masks, profiles and fitted widths for inspection.
    None means no candidate. No reference labels are inputs. No automatic
    metadata updates; final_speed is always None. Morphology selected_speed
    means internal heuristic gate only, not verified physical ground truth.

Historical review preference: global gradient for 800 nm; morphology v2 is
provisional for 1064 nm (four development cases); no preferred method for 690.
Both candidates are always retained. The API performs no filesystem access.

Optional CLI (only explicit user paths are accessed):
    python mf_sound_speed_portable.py --cache sweep.npz --wavelength 800 --out new_output
NPZ fields: full_mips, speeds, axis_x, axis_y. Use --image-key full if needed.
The retained MF validation used full-depth MIPs, not a 121:end Z-slab.
"""
from dataclasses import dataclass, asdict
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.ndimage import (gaussian_filter, binary_opening, binary_closing,
                           map_coordinates, label, convolve, binary_dilation)
from scipy.signal import find_peaks
from skimage.morphology import skeletonize

__version__ = "1.0.0"
__all__ = ["select_sound_speed", "select_speed", "run_cache"]



def gradient_ratio(image, roi):
    a = gaussian_filter(np.asarray(image, dtype='f8'), 1.0)
    gy, gx = np.gradient(a)
    v = a[roi]
    if v.size < 32 or np.var(v) <= 1e-24:
        return None
    return float(np.mean((gx*gx + gy*gy)[roi]) / np.var(v))


def score_stack(images, roi=None, tile_px=64):
    images = np.asarray(images, dtype='f8')
    if images.ndim != 3 or not np.isfinite(images).all():
        raise ValueError('Expected finite speed,Y,X image stack')
    smooth = np.stack([gaussian_filter(a, 1.0) for a in images])
    gy = np.gradient(smooth, axis=1)
    gx = np.gradient(smooth, axis=2)
    gradient_energy = gx*gx + gy*gy
    base = np.percentile(smooth, 10, axis=(1, 2))[:, None, None]
    span = np.percentile(smooth, 99, axis=(1, 2))[:, None, None] - base
    if np.any(span <= 1e-12):
        raise ValueError('No usable contrast')
    consensus = np.median((smooth-base)/span, axis=0)
    foreground = binary_closing(binary_opening(consensus > 0.08), iterations=2)
    support = foreground if roi is None else foreground & np.asarray(roi, bool)
    support[:4] = False; support[-4:] = False
    support[:, :4] = False; support[:, -4:] = False
    curves = []; tiles = []
    for y in range(0, images.shape[1], tile_px):
        for x in range(0, images.shape[2], tile_px):
            sl = np.s_[y:y+tile_px, x:x+tile_px]
            keep = support[sl]
            if keep.sum() < 64:
                continue
            values = smooth[:, sl[0], sl[1]][:, keep]
            energy = gradient_energy[:, sl[0], sl[1]][:, keep].mean(1)
            variance = values.var(1)
            if np.any(variance <= 1e-24):
                continue
            ratio = energy/variance
            curves.append(ratio / ratio.max())
            tiles.append([y, x, int(keep.sum())])
    if len(curves) < 3:
        raise ValueError(f'Only {len(curves)} eligible tiles; no reliable score')
    curves = np.asarray(curves)
    scores = np.median(curves, axis=0)
    global_scores = [gradient_ratio(a, support) for a in images]
    return dict(scores=scores.tolist(), global_normalized_gradient=global_scores,
                eligible_tiles=tiles, tile_score_curves=curves.tolist(),
                roi_pixels=int(support.sum()), method='median_equal_weight_tile_gradient_over_variance',
                sigma_px=1.0, tile_px=tile_px), support


@dataclass(frozen=True)
class VesselConfig:
    ridge_scales_mm: tuple = (.15, .30, .50)
    ridge_threshold: float = .12
    min_segment_mm: float = 3.0
    center_spacing_mm: float = .75
    half_profile_mm: float = 1.5
    recenter_mm: float = .6
    tangent_average_mm: float = .25
    min_width_mm: float = .15
    max_width_mm: float = 1.5
    min_snr: float = 4.0
    min_profiles: int = 12
    min_segments: int = 3


def normalize_stack(images):
    a = np.asarray(images, dtype=float)
    if a.ndim != 3 or not np.isfinite(a).all():
        raise ValueError('Expected finite speed,Y,X full MIPs')
    lo = np.percentile(a, 10, axis=(1,2))[:,None,None]
    scale = np.percentile(a, 99, axis=(1,2))[:,None,None]-lo
    if np.any(scale <= 0):
        raise ValueError('No usable image contrast')
    return (a-lo)/scale


def detect_centers(images, spacing_yx, roi, config):
    consensus = np.median(normalize_stack(images), axis=0)
    sy, sx = spacing_yx
    response = np.zeros_like(consensus)
    for mm in config.ridge_scales_mm:
        sig = (mm/sy, mm/sx)
        yy = gaussian_filter(consensus, sig, order=(2,0))*mm**2/sy**2
        xx = gaussian_filter(consensus, sig, order=(0,2))*mm**2/sx**2
        xy = gaussian_filter(consensus, sig, order=(1,1))*mm**2/(sy*sx)
        h = np.stack([yy,xy,xy,xx], axis=-1).reshape(*yy.shape,2,2)
        eig = np.linalg.eigvalsh(h)
        largest = np.argmax(np.abs(eig), axis=-1)
        big = np.take_along_axis(eig, largest[...,None], axis=-1)[...,0]
        small = np.take_along_axis(eig, (1-largest)[...,None], axis=-1)[...,0]
        strength = np.hypot(big, small)
        c = max(float(np.percentile(strength, 90)), 1e-15)
        r = np.exp(-.5*(small/(np.abs(big)+1e-15)/.5)**2)*(1-np.exp(-.5*(strength/c)**2))
        r[big >= 0] = 0
        response = np.maximum(response, r)
    ridges = response > config.ridge_threshold
    # ROI does not change ridge extraction or impose an artificial image edge.
    skel = skeletonize(ridges)
    degree = convolve(skel.astype('i4'), np.ones((3,3),dtype='i4'), mode='constant')-skel
    junction = skel & (degree > 2)
    skel &= ~binary_dilation(junction, iterations=max(1, round(.4/min(sy,sx))))
    labels, count = label(skel, structure=np.ones((3,3)))
    margin = int(np.ceil((config.half_profile_mm+config.tangent_average_mm)/min(sy,sx)))+2
    points, normals, groups = [], [], []
    for group in range(1,count+1):
        coords = np.argwhere(labels==group)
        if len(coords)*min(sy,sx) < config.min_segment_mm:
            continue
        physical = coords*np.array([sy,sx])
        used_cells = set()
        for p, phys in zip(coords, physical):
            y,x = p
            if min(y,x,consensus.shape[0]-1-y,consensus.shape[1]-1-x) < margin:
                continue
            if roi is not None and not roi[y,x]:
                continue
            cell = tuple(np.floor(phys/config.center_spacing_mm).astype(int))
            if cell in used_cells:
                continue
            neighbours = physical[np.linalg.norm(physical-phys, axis=1)<=1.0]
            if len(neighbours)<5:
                continue
            eig, vec = np.linalg.eigh(np.cov(neighbours.T))
            if eig[-1]<=0 or eig[0]/eig[-1]>.25:
                continue
            points.append(p);normals.append(vec[:,0]);groups.append(group)
            used_cells.add(cell)
    return (np.asarray(points, dtype=float).reshape(-1,2),
            np.asarray(normals, dtype=float).reshape(-1,2), np.asarray(groups), response, labels)


def profile_width(profile, offsets, config):
    p = np.asarray(profile, dtype=float)
    n = max(3, len(p)//10)
    base = np.linspace(np.median(p[:n]), np.median(p[-n:]), len(p))
    q = p-base
    search = np.flatnonzero(np.abs(offsets)<=config.recenter_mm)
    peak = search[np.argmax(q[search])]
    amplitude = q[peak]
    # Local baseline roughness estimates prominence, not the scoring weight.
    tails = np.r_[np.diff(q[:n]), np.diff(q[-n:])]
    noise = np.median(np.abs(tails-np.median(tails)))/(.67448975*np.sqrt(2))
    if amplitude<=0 or amplitude<config.min_snr*noise:
        return np.nan, np.nan
    peaks,_ = find_peaks(q, prominence=.35*amplitude)
    if any(abs(offsets[k]-offsets[peak])>.35 and q[k]>.65*amplitude for k in peaks):
        return np.nan, np.nan
    def crossing(level, direction):
        k = peak
        while 0<=k+direction<len(q):
            j = k+direction
            if q[j]<=level*amplitude:
                if q[k]==q[j]:
                    return np.nan
                return offsets[k]+(offsets[j]-offsets[k])*(level*amplitude-q[k])/(q[j]-q[k])
            k=j
        return np.nan
    l20,l50,l80 = [crossing(v,-1) for v in [.2,.5,.8]]
    r20,r50,r80 = [crossing(v,1) for v in [.2,.5,.8]]
    width = r50-l50
    edge = ((l80-l20)+(r20-r80))/2
    if not np.isfinite(width+edge) or not config.min_width_mm<=width<=config.max_width_mm or edge<=0:
        return np.nan, np.nan
    return width, edge


def score_vessels(images, speeds, axis_x, axis_y, roi=None, config=VesselConfig()):
    a = normalize_stack(images)
    speeds = np.asarray(speeds)
    if len(speeds)!=len(a) or len(np.unique(speeds))!=len(speeds) or len(speeds)<3:
        raise ValueError('At least three distinct speeds are required')
    x,y = np.asarray(axis_x),np.asarray(axis_y)
    if a.shape[1:]!=(len(y),len(x)):
        raise ValueError('XY axes do not match image shape')
    sx,sy = float(np.mean(np.diff(x))),float(np.mean(np.diff(y)))
    if min(sx,sy)<=0 or not np.allclose(np.diff(x),sx,rtol=1e-3) or not np.allclose(np.diff(y),sy,rtol=1e-3):
        raise ValueError('Uniform increasing physical axes required')
    if roi is not None:
        roi=np.asarray(roi,dtype=bool)
        if roi.shape!=a.shape[1:]:raise ValueError('ROI shape mismatch')
    centers,normals,groups,response,labels=detect_centers(a,(sy,sx),roi,config)
    offsets=np.linspace(-config.half_profile_mm,config.half_profile_mm,
                        int(np.ceil(4*config.half_profile_mm/min(sy,sx)))+1)
    tangent=np.stack([-normals[:,1],normals[:,0]],axis=1)
    along=np.linspace(-config.tangent_average_mm,config.tangent_average_mm,5)
    coords=centers[:,None,None,:]+(normals[:,None,None,:]*offsets[None,:,None,None]
            +tangent[:,None,None,:]*along[None,None,:,None])/np.array([sy,sx])
    widths=np.full((len(a),len(centers)),np.nan)
    edges=widths.copy()
    profiles=[]
    for i,im in enumerate(a):
        # Fixed, subpixel interpolation; no speed-specific sharpening/filtering.
        sampled=map_coordinates(im,coords.reshape(-1,2).T,order=1,mode='nearest').reshape(len(centers),len(offsets),5).mean(axis=2)
        profiles.append(sampled)
        for j,p in enumerate(sampled):widths[i,j],edges[i,j]=profile_width(p,offsets,config)
    paired=np.isfinite(widths).all(axis=0)&np.isfinite(edges).all(axis=0)
    eligible=[g for g in np.unique(groups[paired]) if np.sum(paired&(groups==g))>=3]
    paired &= np.isin(groups,eligible)
    audit=dict(centers_yx_px=centers,normals_yx=normals,segment_ids=groups,paired_keep=paired,
               widths_mm=widths,edges_20_80_mm=edges,profiles=np.asarray(profiles),offsets_mm=offsets,
               ridge_response=response,segment_labels=labels)
    result=dict(method='paired_vessel_transverse_FWHM_v1',config=asdict(config),
                detected_profiles=len(centers),paired_profiles=int(paired.sum()),segments=len(eligible),
                candidate=None,selected_speed=None,flags=[],speeds=speeds.tolist())
    if paired.sum()<config.min_profiles or len(eligible)<config.min_segments:
        result.update(status='insufficient_vessels',flags=['insufficient_common_valid_vessel_segments'])
        return result,audit
    def aggregate(values):
        # Normalize each fixed location by its speed-median width, not its brightness.
        ratios=np.median(values[:,paired],axis=0)[None,:]/values[:,paired]
        segment=np.stack([np.median(ratios[:,groups[paired]==g],axis=1) for g in eligible])
        return np.median(segment,axis=0),segment
    scores,segment_curves=aggregate(widths)
    edge_scores,_=aggregate(edges)
    chosen=int(speeds[np.argmax(scores)]);edge_chosen=int(speeds[np.argmax(edge_scores)])
    flags=[]
    if chosen in [speeds.min(),speeds.max()]:flags.append('range_endpoint')
    if abs(chosen-edge_chosen)>2:flags.append('width_edge_disagreement_over_2')
    if np.ptp(scores)/scores.max()<.01:flags.append('flat_curve_under_1pct')
    if paired.sum()/max(len(centers),1)<.2:flags.append('low_profile_retention')
    winners=speeds[np.argmax(segment_curves,axis=1)]
    agreement=float(np.mean(np.abs(winners-chosen)<=2))
    if agreement<.5:flags.append('segment_disagreement')
    result.update(status='requires_review' if flags else 'candidate',candidate=chosen,
                  selected_speed=None if flags else chosen,edge_candidate=edge_chosen,flags=flags,
                  scores=scores.tolist(),edge_scores=edge_scores.tolist(),
                  median_FWHM_mm=np.median(widths[:,paired],axis=1).tolist(),
                  median_edge_mm=np.median(edges[:,paired],axis=1).tolist(),
                  segment_winners=winners.tolist(),segment_agreement_le2=agreement)
    audit['segment_score_curves']=segment_curves
    return result,audit


@dataclass(frozen=True)
class MorphologyConfig:
    min_profile_r2: float = .65
    min_valid_fraction: float = .8
    min_focus_r2: float = .4
    min_logwidth_change: float = .05
    max_position_residual_mm: float = .15
    region_mm: float = 10.
    min_tracks: int = 12
    min_segments: int = 3
    min_regions: int = 3
    min_region_agreement: float = .6
    max_bootstrap_span_m_s: float = 4.


def fit_profiles(profiles, offsets):
    """Gaussian ridge + affine baseline, positive free amplitude, free center.

Eliminate linear nuisance terms by orthogonal projection. Exhaustive template
matching avoids nonlinear optimizer initialization; interpolate width locally.
Returns descriptive width and residual diagnostics, not anatomical diameter.
"""
    p=np.asarray(profiles,float);t=np.asarray(offsets,float)
    if not np.isfinite(p).all() or p.shape[-1]!=len(t):
        raise ValueError('Finite, aligned transverse profiles required')
    basis=np.stack([np.ones_like(t),t],axis=1)
    q,_=np.linalg.qr(basis)
    flat=p.reshape(-1,len(t))
    residual=flat-(flat@q)@q.T
    norms=np.linalg.norm(residual,axis=1)
    safe=norms>np.maximum(np.linalg.norm(flat,axis=1)*1e-12,1e-14)
    normalized=np.divide(residual,norms[:,None],out=np.zeros_like(residual),where=safe[:,None])
    logsigma=np.linspace(np.log(.05),np.log(.9),33)
    centers=np.linspace(-.7,.7,29)
    templates=np.exp(-.5*((t[None,None,:]-centers[None,:,None])/np.exp(logsigma[:,None,None]))**2)
    templates=templates.reshape(-1,len(t))
    templates-= (templates@q)@q.T
    templates/=np.linalg.norm(templates,axis=1)[:,None]
    # Dot products are invariant to positive gain and an affine baseline.
    corr=normalized@templates.T
    best=np.argmax(corr,axis=1);si,ci=np.unravel_index(best,(len(logsigma),len(centers)))
    ridx=np.arange(len(flat));peak=corr[ridx,best]
    shaped=corr.reshape(len(flat),len(logsigma),len(centers))
    left=shaped[ridx,np.maximum(si-1,0),ci]
    right=shaped[ridx,np.minimum(si+1,len(logsigma)-1),ci]
    denom=left-2*peak+right
    delta=np.divide(.5*(left-right),denom,out=np.zeros_like(peak),where=denom < -1e-12)
    delta=np.clip(delta,-1,1)
    sigma=np.exp(logsigma[si]+delta*(logsigma[1]-logsigma[0]))
    fwhm=2*np.sqrt(2*np.log(2))*sigma
    valid=safe&(peak>0)&(si>0)&(si<len(logsigma)-1)&(ci>0)&(ci<len(centers)-1)
    fwhm[~valid]=np.nan
    result_shape=p.shape[:-1]
    return (fwhm.reshape(result_shape), np.where(valid,peak**2,0).reshape(result_shape),
            centers[ci].reshape(result_shape))


def robust_quadratic(x,y):
    matrix=np.stack([x*x,x,np.ones_like(x)],axis=1)
    weights=np.ones(len(x))
    for _ in range(6):
        root=np.sqrt(weights)
        beta=np.linalg.lstsq(matrix*root[:,None],y*root,rcond=None)[0]
        residual=y-matrix@beta
        scale=max(1.4826*np.median(np.abs(residual-np.median(residual))),1e-8)
        weights=np.minimum(1,1.5*scale/np.maximum(np.abs(residual),1e-12))
    r2=1-np.sum(weights*residual**2)/max(np.sum(weights*(y-np.average(y,weights=weights))**2),1e-15)
    return beta,float(r2),residual


def infer_tracks(widths, fit_r2, positions, speeds, cfg):
    speeds=np.asarray(speeds,float)
    scale=(speeds.max()-speeds.min())/2;mid=(speeds.max()+speeds.min())/2
    x=(speeds-mid)/scale
    n=widths.shape[1]
    opt=np.full(n,np.nan);trend_r2=np.full(n,np.nan)
    reasons=np.full(n,'insufficient_valid_profiles',dtype='<U40')
    valid=np.isfinite(widths)&(fit_r2>=cfg.min_profile_r2)
    for j in range(n):
        keep=valid[:,j]
        if keep.sum()<max(5,int(np.ceil(len(speeds)*cfg.min_valid_fraction))):continue
        beta,r2,_=robust_quadratic(x[keep],np.log(widths[keep,j]))
        trend_r2[j]=r2
        if beta[0]<=0 or r2<cfg.min_focus_r2:
            reasons[j]='no_convincing_convex_focus_trend';continue
        vertex=-beta[1]/(2*beta[0]);speed=mid+scale*vertex
        if speed<=speeds.min() or speed>=speeds.max():
            reasons[j]='focus_outside_range';continue
        predicted=np.polyval(beta,x)
        if np.ptp(predicted)<cfg.min_logwidth_change:
            reasons[j]='width_trend_too_flat';continue
        local=np.abs(speeds-speed)<=2
        if np.sum(local&keep)<3:
            reasons[j]='unmeasured_near_optimum';continue
        _,_,residual=robust_quadratic(x[keep],positions[keep,j])
        if np.sqrt(np.mean(residual**2))>cfg.max_position_residual_mm:
            reasons[j]='unstable_vessel_position';continue
        opt[j]=speed;reasons[j]='accepted'
    return opt,trend_r2,valid,reasons


def aggregate_regions(optima, groups, centers_yx, spacing_yx, speeds, cfg):
    segments=[]
    for group in np.unique(groups[np.isfinite(optima)]):
        keep=np.isfinite(optima)&(groups==group)
        if keep.sum()<2:continue
        location=np.median(centers_yx[keep]*np.asarray(spacing_yx),axis=0)
        region=tuple(np.floor(location/cfg.region_mm).astype(int))
        segments.append((int(group),float(np.median(optima[keep])),region,int(keep.sum())))
    regions=sorted(set(v[2] for v in segments))
    votes=np.array([np.median([v[1] for v in segments if v[2]==r]) for r in regions])
    result=dict(candidate=None,selected_speed=None,accepted_tracks=int(sum(v[3] for v in segments)),
                segments=len(segments),regions=len(regions),flags=[],status='insufficient_evidence',
                region_optima=votes.tolist(),segment_optima=[v[1] for v in segments])
    if result['accepted_tracks']<cfg.min_tracks or len(segments)<cfg.min_segments or len(regions)<cfg.min_regions:
        result['flags']=['insufficient_spatially_distributed_vessels'];return result
    estimate=float(np.median(votes))
    candidate=int(speeds[np.argmin(np.abs(np.asarray(speeds)-estimate))])
    rng=np.random.default_rng(42)
    boot=np.median(rng.choice(votes,(1000,len(votes)),replace=True),axis=1)
    interval=np.percentile(boot,[2.5,97.5])
    agreement=float(np.mean(np.abs(votes-candidate)<=2))
    loo=np.array([np.median(np.delete(votes,i)) for i in range(len(votes))])
    flags=[]
    if candidate in [min(speeds),max(speeds)]:flags.append('range_endpoint')
    if agreement<cfg.min_region_agreement:flags.append('regional_disagreement')
    if interval[1]-interval[0]>cfg.max_bootstrap_span_m_s:flags.append('unstable_region_resampling')
    if np.max(np.abs(loo-estimate))>2:flags.append('sensitive_to_one_region')
    result.update(candidate=candidate,selected_speed=None if flags else candidate,
                  estimate_m_s=estimate,region_agreement_le2=agreement,
                  region_resampling_interval=interval.tolist(),flags=flags,
                  status='requires_review' if flags else 'candidate')
    return result


def from_profiles(audit,speeds,axis_x,axis_y,cfg=MorphologyConfig()):
    x,y=np.asarray(axis_x),np.asarray(axis_y)
    spacing=(float(np.mean(np.diff(y))),float(np.mean(np.diff(x))))
    widths,r2,mu=fit_profiles(audit['profiles'],audit['offsets_mm'])
    # Below this sampling limit, fitted subpixel widths are not trusted.
    r2[widths<1.5*max(spacing)]=0
    opt,trend,valid,reasons=infer_tracks(widths,r2,mu,speeds,cfg)
    result=aggregate_regions(opt,audit['segment_ids'],audit['centers_yx_px'],spacing,np.asarray(speeds),cfg)
    result.update(method='morphology_adaptive_profile_trends_v2',config=asdict(cfg),
                  detected_profiles=int(widths.shape[1]),speeds=np.asarray(speeds).tolist(),
                  rejection_counts={str(k):int(np.sum(reasons==k)) for k in np.unique(reasons)},
                  uncertainty_note='Region-resampling sensitivity, not a calibrated sound-speed confidence interval.')
    detail=dict(fitted_FWHM_mm=widths,profile_r2=r2,peak_position_mm=mu,track_optimum=opt,
                focus_trend_r2=trend,valid_profiles=valid,rejection_reason=reasons,
                centers_yx_px=audit['centers_yx_px'],segment_ids=audit['segment_ids'])
    return result,detail


def score_morphology(images,speeds,axis_x,axis_y,roi=None,cfg=MorphologyConfig()):
    # Only reuse v1's label-free geometry/profile extraction; discarded v1
    # threshold-crossing widths do not gate the new fitted-profile method.
    _,audit=score_vessels(images,speeds,axis_x,axis_y,roi)
    result,detail=from_profiles(audit,speeds,axis_x,axis_y,cfg)
    detail.update(profiles=audit['profiles'],offsets_mm=audit['offsets_mm'])
    return result,detail


def validate_input(images, speeds, axis_x, axis_y):
    a, s, x, y = map(np.asarray, (images, speeds, axis_x, axis_y))
    if a.ndim != 3 or s.ndim != 1 or x.ndim != 1 or y.ndim != 1:
        raise ValueError("Expected images[speed,Y,X] and 1-D speeds/axis_x/axis_y")
    if min(len(x), len(y)) < 8 or a.shape != (len(s), len(y), len(x)):
        raise ValueError("Image shape must match speed,Y,X axes (at least 8 pixels per axis)")
    if not all(np.issubdtype(v.dtype, np.number) and not np.iscomplexobj(v)
               and np.isfinite(v).all() for v in (a, s, x, y)):
        raise ValueError("Real finite numeric inputs required; no RGB, NaN or object arrays")
    if not np.array_equal(s, np.arange(1490, 1511)):
        raise ValueError("This frozen MF package requires speeds 1490:1:1510, in increasing order")
    for name, axis in (("X", x), ("Y", y)):
        delta = np.diff(axis.astype(float))
        if np.any(delta <= 0) or not np.allclose(delta, delta.mean(), rtol=1e-3):
            raise ValueError(f"{name} axis must be uniformly increasing, in millimetres")
    return a, s, x, y


def select_speed(images, speeds, axis_x, axis_y, wavelength_nm):
    """Return (two independent candidate records, audit arrays).

    Wavelength sets review priority only. Both frozen algorithms see the same
    complete numeric images and never receive wavelength or reference speed.
    The package does not turn candidate suggestions into production metadata.
    """
    (a, s, x, y) = validate_input(images, speeds, axis_x, axis_y)
    if wavelength_nm not in (690, 800, 1064):
        raise ValueError('Supported recorded MF wavelengths: 690, 800, 1064 nm')
    priority = {800: 'full_global_normalized_gradient', 1064: 'morphology_v2_provisional_manual_review', 690: 'no_validated_preference'}[wavelength_nm]
    (timings, details) = ({}, {})
    start = time.perf_counter()
    try:
        (record, support) = score_stack(a)
        curve = np.asarray(record['global_normalized_gradient'], dtype=float)
        if not np.isfinite(curve).all():
            raise ValueError('Nonfinite gradient curve')
        winners = np.flatnonzero(np.isclose(curve, curve.max(), rtol=1e-12, atol=0))
        candidate = int(s[winners[0]]) if len(winners) == 1 else None
        flags = []
        if candidate is None:
            flags.append('tied_candidates')
        if candidate in (int(s[0]), int(s[-1])):
            flags.append('range_endpoint')
        gradient = dict(candidate=candidate, scores=curve.tolist(), tied_candidates=s[winners].astype(int).tolist(), support_pixels=int(support.sum()), flags=flags, status='requires_review' if flags else 'candidate', gate_calibrated=False)
        details['gradient_support_yx'] = support
    except ValueError as exc:
        gradient = dict(candidate=None, scores=None, status='insufficient_evidence', flags=['gradient_unavailable'], reason=str(exc), gate_calibrated=False)
    timings['global_gradient_s'] = time.perf_counter() - start
    start = time.perf_counter()
    try:
        (morphology, audit) = score_morphology(a, s, x, y)
        details.update({'morphology_' + key: value for (key, value) in audit.items()})
    except ValueError as exc:
        morphology = dict(candidate=None, selected_speed=None, status='insufficient_evidence', flags=['morphology_unavailable'], reason=str(exc))
    timings['morphology_s'] = time.perf_counter() - start
    result = dict(schema_version='1.0', methods=dict(full_global_normalized_gradient=gradient, morphology_v2=morphology), speeds_m_s=s.tolist(), wavelength_nm=int(wavelength_nm), review_priority=priority, final_speed=None, automatic_writeback=False, reference_used_by_algorithm=False, independent_validation_passed=False, production_modified=False, timing_s=timings, input_domain='complete_numeric_XY_MIP')
    return (result, details)


def run_cache(cache, out, wavelength_nm, image_key="full_mips"):
    cache, out = Path(cache), Path(out)
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite output directory: {out}")
    if image_key not in ("full_mips", "full"):
        raise ValueError("Complete numeric MIPs required, not surface_mips or masked mips")
    start = time.perf_counter()
    with np.load(cache, allow_pickle=False) as data:
        images, speeds, x, y = (data[k] for k in (image_key, "speeds", "axis_x", "axis_y"))
    io_s = time.perf_counter() - start
    result, audit = select_speed(images, speeds, x, y, wavelength_nm)
    result.update(cache=str(cache.resolve()), image_key=image_key,
                  cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest())
    result["timing_s"]["cache_read_s"] = io_s
    result["timing_s"]["before_export_s"] = time.perf_counter() - start
    out.mkdir(parents=True, exist_ok=False)
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                               allow_nan=False) + "\n", encoding="utf-8")
    np.savez_compressed(out / "audit.npz", speeds=speeds, axis_x=x, axis_y=y, **audit)
    with (out / "candidates.csv").open("x", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["method", "candidate_m_s", "internal_gate_candidate_m_s", "status", "flags"])
        for name, record in result["methods"].items():
            writer.writerow([name, record["candidate"], record.get("selected_speed"),
                             record["status"], ";".join(record["flags"])])
    with (out / "gradient_curve.csv").open("x", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["speed_m_s", "full_global_normalized_gradient"])
        scores = result["methods"]["full_global_normalized_gradient"]["scores"]
        writer.writerows(zip(speeds.tolist(), scores if scores is not None else [None]*len(speeds)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="New directory; never overwrites")
    parser.add_argument("--wavelength", required=True, type=int, choices=[690, 800, 1064])
    parser.add_argument("--image-key", choices=["full_mips", "full"], default="full_mips")
    args = parser.parse_args()
    result = run_cache(args.cache, args.out, args.wavelength, args.image_key)
    print(json.dumps({"candidates": {k: v["candidate"] for k, v in result["methods"].items()},
                      "review_priority": result["review_priority"], "final_speed": None,
                      "output": str(args.out.resolve())}, ensure_ascii=False, indent=2))


select_sound_speed = select_speed

if __name__ == "__main__":
    main()
