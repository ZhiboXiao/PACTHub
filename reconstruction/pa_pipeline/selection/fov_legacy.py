"""独立 XY-MIP 区域分割与 FOV 角度标定（无 BP、文件读取或绘图）。

依赖：numpy、scipy、opencv-python（或 opencv-python-headless）。
来源：Pipeline/fov_geometry.py，保留原有六个计算函数，未改分割阈值。
原文件 SHA256: 7c86a935b52c914825cd0fcfddb5edbe03166c8a70280bfd6b628d2c719a6bce

推荐入口：
    result, mask = select_fov(
        mip_yx, center_mm=(0, 0, -4), space_mm=(100, 100, 20))
    angle_deg = result["initial_z_rotation_deg"]
    center_new = result["center_rotated_mm"]
    Rz = np.asarray(result["rotation_matrix_z"])
    detector_new = detector @ Rz.T

输入是原始、未旋转、未带标注的二维 XY-MIP；列是 +X，行是 +Y。
MATLAB 的 max(volume,[],3) 为 [X,Y]，传入前转置为 [Y,X]；
已有 imwrite(xymip') PNG 数组不再转置。不传显示截图或彩色图。
不读取样本 JSON，不推断 scan 位置；调用方必须传当前采集的大视场中心。
XY 采样间距应相同（允许网格取整造成的 2% 差异）；毫米为长度单位。
默认血管结构补充 + 上尾 4 sigma，最多约 1% ROI 像素被截顶。
此截顶只作用于分割副本，不修改输入图像，不旋转或重采样图像。
目标 FOV 固定 [40,80,20] mm，长轴沿 Y。Z 中心保持输入值。
输出是可见 PA 信息区域，不是真实皮肤分割；不能识别头尾，保留 180° 歧义。
异常/空白输入抛出 ValueError；正常输出仍需要审核 segmentation_flags。
"""

import cv2
import numpy as np
from scipy import ndimage as ndi


def rotation(degrees):
    t = np.deg2rad(degrees)
    return np.array([[np.cos(t), -np.sin(t), 0],
                     [np.sin(t), np.cos(t), 0], [0, 0, 1.]])


def rectangle(center, long_axis, length, width):
    v = np.asarray(long_axis)
    u = np.array([v[1], -v[0]])
    return np.array([np.asarray(center) + a * length / 2 * v + b * width / 2 * u
                     for a, b in [(-1, -1), (-1, 1), (1, 1), (1, -1)]])


def geometry(mask, x, y, z=-4., axis_method='pca'):
    rows, cols = np.nonzero(mask)
    points = np.column_stack([x[cols], y[rows]])
    if len(points) < 20:
        raise ValueError('Insufficient segmented foreground; automatic FOV withheld')
    cov = np.cov(points.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    fitted = cv2.minAreaRect(points.astype('float32'))
    corners = cv2.boxPoints(fitted).astype(float)
    edges = np.roll(corners,-1,axis=0)-corners
    min_rect_axis = edges[np.argmax(np.linalg.norm(edges,axis=1))]
    min_rect_axis = min_rect_axis/np.linalg.norm(min_rect_axis)
    if min_rect_axis[1]<0: min_rect_axis=-min_rect_axis
    # Global second-moment axis uses all accepted regions. The direction of one
    # supporting edge of a minimum-area box is not the global anatomical axis.
    if axis_method=='pca': v=eigenvectors[:,-1]
    elif axis_method=='min_area_rectangle': v=min_rect_axis
    else: raise ValueError('Unknown axis estimation method')
    if v[1] < 0:
        v = -v
    u = np.array([v[1], -v[0]])
    vl, vh = np.min(points @ v), np.max(points @ v)
    ul, uh = np.min(points @ u), np.max(points @ u)
    center_xy = (vl + vh) / 2 * v + (ul + uh) / 2 * u
    angle = float(np.rad2deg(np.arctan2(v[0], v[1])))
    center = np.r_[center_xy, z]
    ratio = float(eigenvalues[-1] / max(eigenvalues[0], 1e-12))
    return dict(center_native_mm=center.tolist(),
                center_rotated_mm=(rotation(angle) @ center).tolist(),
                initial_z_rotation_deg=angle, long_axis_xy=v.tolist(),
                fitted_length_mm=float(vh-vl), fitted_width_mm=float(uh-ul),
                axis_eigenvalue_ratio=ratio,
                axis_method=axis_method,
                minimum_area_rectangle_angle_deg=float(np.rad2deg(np.arctan2(min_rect_axis[0],min_rect_axis[1]))),
                fitted_rectangle_xy_mm=rectangle(center_xy, v, vh-vl, uh-ul).tolist(),
                target_rectangle_xy_mm=rectangle(center_xy, v, 80, 40).tolist(),
                target_space_xyz_mm=[40., 80., 20.],
                head_tail_status='unresolved_180_degree_ambiguity',
                orientation_status='axis_only_not_anatomical_head_tail',
                coordinate_convention='native PNG: columns +X right; rows +Y down; no image rotation',
                angle_convention='additional active CCW Z rotation in physical XY: sensor_new=sensor*Rz.T; center_new=center*Rz.T')


def vessel_extension(values, contrast, threshold, base_mask, allowed, background_region, px_per_mm, diagnostics=None):
    """Image-domain shape evidence only: multiscale bright ridges + hysteresis.

    Keep the conservative attached-ridge route, plus independently qualified
    continuous ridge components. The original reconstruction is untouched.
    """
    response=np.zeros_like(values,dtype=float)
    tangent=np.zeros_like(values,dtype=float)
    persistence=np.zeros_like(values,dtype=np.uint8)
    scales_mm=[.2,.35,.5,.8,1.2]
    for mm in scales_mm:
        sigma=max(1.,mm*px_per_mm)
        hyy=ndi.gaussian_filter(values,sigma,order=(2,0))*sigma**2
        hxx=ndi.gaussian_filter(values,sigma,order=(0,2))*sigma**2
        hxy=ndi.gaussian_filter(values,sigma,order=(1,1))*sigma**2
        disc=np.sqrt((hxx-hyy)**2+4*hxy**2)
        eig_a=(hxx+hyy-disc)/2
        eig_b=(hxx+hyy+disc)/2
        swap=np.abs(eig_a)>np.abs(eig_b)
        small=np.where(swap,eig_b,eig_a)
        large=np.where(swap,eig_a,eig_b)
        strength=np.hypot(small,large)
        amplitude_scale=max(float(np.percentile(strength[allowed],90))*.5,1e-6)
        shape=np.exp(-.5*(np.abs(small)/(np.abs(large)+1e-12)/.5)**2)
        signal=1-np.exp(-.5*(strength/amplitude_scale)**2)
        ridge=np.where(large<0,shape*signal,0)
        better=ridge>response
        tangent[better]=(.5*np.arctan2(2*hxy,hxx-hyy))[better]
        persistence+=(ridge>=.2).astype(np.uint8)
        response=np.maximum(response,ridge)
    # Speckle can look line-like at one scale, but nearby vessel tangents should
    # agree across a short physical neighborhood and persist across scales.
    coherence_sigma=.7*px_per_mm
    denom=ndi.gaussian_filter(response,coherence_sigma)+1e-12
    direction_x=ndi.gaussian_filter(response*np.cos(2*tangent),coherence_sigma)/denom
    direction_y=ndi.gaussian_filter(response*np.sin(2*tangent),coherence_sigma)/denom
    coherence=np.hypot(direction_x,direction_y)
    background=response[background_region]
    median=float(np.median(background));mad=float(np.median(np.abs(background-median))*1.4826)
    low=max(.20,median+2*mad)
    high=max(.40,median+4*mad)
    raw_bg=values[background_region]
    raw_median=float(np.median(raw_bg))
    raw_mad=float(np.median(np.abs(raw_bg-raw_median))*1.4826)
    raw_floor=max(raw_median+3*raw_mad,threshold*.05,1e-6)
    # Broad background subtraction can cancel a weak vessel beside a bright
    # organ. Preserve its independently supported ridge in the original MIP.
    signal_support=(contrast>threshold*.15)|(values>raw_floor)
    evidence=(response>=low)&(coherence>=.7)&(persistence>=2)&signal_support&allowed
    rad=max(1,round(.3*px_per_mm))
    bridge=cv2.morphologyEx(evidence.astype('uint8'),cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*rad+1,2*rad+1))).astype(bool)&allowed
    anchor_rad=max(1,round(2.*px_per_mm))
    anchor=cv2.dilate(base_mask.astype('uint8'),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*anchor_rad+1,2*anchor_rad+1))).astype(bool)
    seeds=anchor&(response>=high)&evidence
    connected=ndi.binary_propagation(seeds,structure=np.ones((3,3)),mask=bridge|base_mask)
    if diagnostics is not None:
        diagnostics.update(ridge_response=response, direction_coherence=coherence,
                           scale_persistence=persistence, signal_support=signal_support,
                           ridge_evidence=evidence, ridge_bridge=bridge, ridge_seeds=seeds,
                           ridge_connected=connected, ridge_tangent=tangent)
    # Bridging supports connectivity but never becomes invented signal pixels.
    added=connected&evidence&~base_mask
    labels,n=ndi.label(connected,structure=np.ones((3,3)))
    accepted=np.zeros_like(added)
    for i,sl in enumerate(ndi.find_objects(labels),1):
        if sl is None:continue
        region=labels[sl]==i
        evidence_area=float((region&evidence[sl]).sum()/px_per_mm**2)
        extent=max(sl[0].stop-sl[0].start,sl[1].stop-sl[1].start)/px_per_mm
        if evidence_area>=1 and extent>=2:
            accepted[sl]|=region&added[sl]
    # Pointwise high coherence breaks at bifurcations and textured/weak sections.
    # Qualify whole continuous tracks instead: permit lower pointwise coherence,
    # but require sustained line response, length, and aggregate coherence.
    # These tracks need not touch a thresholded bright organ. Gap closing only
    # establishes topology; it never adds pixels without measured ridge evidence.
    track_evidence=(response>=low)&(coherence>=.45)&(persistence>=2)&signal_support&allowed
    track_rad=max(1,round(.4*px_per_mm))
    tracks=cv2.morphologyEx(track_evidence.astype('uint8'),cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*track_rad+1,2*track_rad+1))).astype(bool)&allowed
    track_labels,_=ndi.label(tracks,structure=np.ones((3,3)))
    track_added=np.zeros_like(accepted);track_records=[]
    for i,sl in enumerate(ndi.find_objects(track_labels),1):
        if sl is None:continue
        region=(track_labels[sl]==i)&track_evidence[sl]
        rows,cols=np.nonzero(region)
        if len(rows)<20:continue
        points=np.column_stack([cols,rows]).astype('float32')
        _,sides,_=cv2.minAreaRect(points)
        length=max(sides)/px_per_mm
        if length<5:continue
        area=len(rows)/px_per_mm**2
        width=area/length
        mean_response=float(response[sl][region].mean())
        mean_coherence=float(coherence[sl][region].mean())
        keep=width<=3 and mean_response>=.75 and mean_coherence>=.6
        track_records.append(dict(label=i,length_mm=length,effective_width_mm=width,
            mean_ridge_response=mean_response,mean_direction_coherence=mean_coherence,
            accepted=keep,centroid_native_pixel_xy=[float(cols.mean()+sl[1].start),float(rows.mean()+sl[0].start)]))
        if keep:track_added[sl]|=region&~base_mask[sl]
    accepted|=track_added
    if diagnostics is not None:
        diagnostics.update(track_evidence=track_evidence,independent_track_added=track_added)
    report=dict(enabled=True,method='multiscale_Hessian_attached_hysteresis_and_independent_continuous_tracks',
                gaussian_scales_mm=scales_mm,low_ridge_threshold=low,high_ridge_threshold=high,
                minimum_local_contrast_fraction=.15,connectivity_gap_closing_radius_mm=.3,
                original_mip_signal_floor=raw_floor,
                minimum_direction_coherence=.7,coherence_neighborhood_sigma_mm=.7,
                minimum_supporting_scales=2,
                baseline_attachment_tolerance_mm=2.,
                requires_connection_to_baseline=False,
                independent_track_criteria=dict(minimum_pointwise_coherence=.45,
                    minimum_length_mm=5.,maximum_effective_width_mm=3.,
                    minimum_mean_ridge_response=.75,minimum_mean_coherence=.6,
                    connectivity_gap_closing_radius_mm=.4),
                independent_track_records=track_records,
                added_area_mm2=float(accepted.sum()/px_per_mm**2),
                added_pixels=int(accepted.sum()),note='Shape evidence is not a validated vessel label; connected artifacts can also be line-like. No reconstructed pixel is altered.')
    return accepted,response,report


def conservative_sigma_clip(values, allowed, sigma=6.):
    """One-pass upper-tail winsorization, segmentation copy only.

    Keep approximately >=99% of ROI pixels untouched. No lower clipping, iteration or
    replacement by zero. A high anatomical signal is capped, not discarded.
    """
    values=np.asarray(values,dtype=float)
    if not np.isfinite(sigma) or sigma<3:raise ValueError('Conservative sigma must be >=3')
    roi=values[allowed]
    if not len(roi) or not np.isfinite(values).all():raise ValueError('Finite nonempty ROI required')
    mean=float(roi.mean());std=float(roi.std())
    floor=float(np.percentile(roi,99.0))
    upper=max(mean+sigma*std,floor)
    changed=(values>upper)&allowed
    output=values.copy();output[changed]=upper
    return output,dict(enabled=True,method='single_pass_upper_only_winsorization',
        sigma=float(sigma),center='mean',scale='population_std',iterations=1,
        mean=mean,std=std,upper_limit=upper,safety_percentile=99.0,
        safety_percentile_value=floor,changed_pixels=int(changed.sum()),
        changed_roi_fraction=float(changed.sum()/len(roi)),
        scope='segmentation_copy_only',lower_tail_untouched=True,
        note='Not RF/temporal clipping, not validated vessel denoising; no source/reconstruction pixel modified.')


def segment(values, center=(0., 0., -4.), space=(150., 150., 20.), vessel_prior=False, diagnostics=None, sigma_upper=None):
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all() or np.ptp(values) <= 0:
        raise ValueError('Invalid/constant XY MIP; no segmentation or rotation proposed')
    h, w = values.shape
    x = np.linspace(center[0]-space[0]/2, center[0]+space[0]/2, w)
    y = np.linspace(center[1]-space[1]/2, center[1]+space[1]/2, h)
    xx, yy = np.meshgrid(x, y)
    radius = np.hypot(xx-center[0], yy-center[1])
    scale = (w-1)/space[0]
    search_radius=min(55.,min(space[:2])/2-5.)
    sigma_report=dict(enabled=False)
    segmentation_values=values
    if sigma_upper is not None:
        segmentation_values,sigma_report=conservative_sigma_clip(values,radius<=search_radius,sigma_upper)
    if diagnostics is not None:
        diagnostics['sigma_clipped_pixels']=segmentation_values!=values
    # Intensity clipping is solely for segmentation. Saved reconstruction unchanged.
    lo, hi = np.percentile(segmentation_values[radius<=search_radius], [1, 99.9])
    clipped = np.clip((segmentation_values-lo)/max(hi-lo, 1e-12), 0, 1)
    # Remove slowly varying sensitivity/speckle background; retain local anatomy.
    smooth = np.maximum(ndi.gaussian_filter(clipped, .55*scale)
                        - ndi.gaussian_filter(clipped, 6.*scale), 0)
    allowed = radius <= search_radius
    background_region=(radius >= search_radius-10) & (radius <= search_radius+10)
    background = smooth[background_region]
    median = float(np.median(background))
    mad = float(np.median(np.abs(background-median))*1.4826)
    otsu, _ = cv2.threshold(np.uint8(np.clip(smooth[allowed]*255, 0, 255)),
                            0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    threshold = max(otsu/255, median + 3*mad)
    initial = (smooth > threshold) & allowed
    rad = max(1, round(3.*scale))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*rad+1, 2*rad+1))
    closed = cv2.morphologyEx(initial.astype('uint8'), cv2.MORPH_CLOSE, disk)
    mask = ndi.binary_fill_holes(closed) & allowed
    labels, count = ndi.label(mask)
    accepted_labels=[]
    components=[]
    pixel_area = (x[1]-x[0])*(y[1]-y[0])
    for i, slices in enumerate(ndi.find_objects(labels), 1):
        if slices is None:
            continue
        region = labels[slices] == i
        area = float(region.sum()*pixel_area)
        rows, cols = np.nonzero(region)
        cx = float(x[cols+slices[1].start].mean())
        cy = float(y[rows+slices[0].start].mean())
        peak=float(smooth[slices][region].max())
        signal_area=float((initial[slices]&region).sum()*pixel_area)
        accepted=3<=area<=6500 and signal_area>=1 and peak>=1.5*threshold
        if accepted:accepted_labels.append(i)
        if area>=.5:
            components.append(dict(label=i,area_mm2=area,signal_area_mm2=signal_area,
                                   centroid_xy_mm=[cx,cy],peak_local_contrast=peak,
                                   accepted=accepted,
                                   decision='global_signal_region' if accepted else 'small_or_low_contrast_component'))
    # No largest-component / distance-to-main restriction: isolated, informative
    # anatomy participates in BOTH center and orientation estimation.
    mask=np.isin(labels,accepted_labels)
    area=float(mask.sum()*pixel_area)
    if area<80:raise ValueError('Insufficient total anatomical signal area; manual review required')
    baseline_result=geometry(mask,x,y,center[2])
    prior_report=dict(enabled=False)
    if vessel_prior:
        added,response,prior_report=vessel_extension(clipped,smooth,threshold,mask,allowed,background_region,scale,diagnostics)
        if diagnostics is not None:
            diagnostics.update(baseline_mask=mask.copy(),weak_added_mask=added,vesselness=response)
        mask|=added
        area=float(mask.sum()*pixel_area)
    result = geometry(mask, x, y, center[2])
    flags = []
    if result['axis_eigenvalue_ratio'] < 1.5:
        flags.append('weak_long_axis')
    if result['fitted_length_mm'] > 80 or result['fitted_width_mm'] > 40:
        flags.append('foreground_exceeds_target_fov')
    if np.any(mask & (radius > search_radius-2)):
        flags.append('foreground_touches_search_limit')
    result.update(segmentation_method='local_contrast_otsu_MAD_global_significant_components_PCA_oriented_bounds',
                  accepted_component_count=len(accepted_labels),component_records=components,
                  component_distance_limit_mm=None,
                  segmentation_scope='visible_PA_anatomy_ROI_not_validated_full_mouse_body_boundary',
                  segmentation_area_mm2=area, segmentation_threshold=threshold,
                  segmentation_flags=flags, axis_geometry_needs_review=bool(flags),
                  needs_review=True, auto_apply_eligible=False,
                  z_source='user_initial_center_held_fixed_XYMIP_does_not_estimate_Z',
                  large_center_mm=list(center), large_space_mm=list(space),
                  segmentation_search_radius_mm=search_radius)
    result['vessel_shape_prior']=prior_report
    result['sigma_clipping']=sigma_report
    if vessel_prior:
        result['without_vessel_prior_geometry']={k:baseline_result[k] for k in ['center_native_mm','initial_z_rotation_deg','axis_eigenvalue_ratio','fitted_length_mm','fitted_width_mm']}
    return result, mask, x, y

def select_fov(mip_yx, center_mm, space_mm, *, vessel_prior=True, sigma_upper=4.0):
    """返回 (result, mask)：物理几何参数字典，以及同输入尺寸的 bool 掩膜。

    result 的主要字段：
      center_native_mm: 原物理坐标系下的选区中心 [x,y,z]。
      center_rotated_mm: 对中心绕全局 Z 轴旋转后的 [x,y,z]。
      initial_z_rotation_deg: 将选区长轴对齐 Y 的主动旋转角（度）。
      rotation_matrix_z: 3x3 旋转矩阵，行向量坐标用 points @ Rz.T。
      fitted_rectangle_xy_mm: 分割区域的定向包围框（原坐标系）。
      target_rectangle_xy_mm: 固定 40x80 mm 目标框（原坐标系）。
      segmentation_flags: 弱方向、超出目标视场、触及搜索范围等提示。

    mask 是信号分割区域，不是整个目标矩形的填充掩膜。
    不修改 detector；调用方需将 Rz 同时应用于探测器坐标和重建中心。
    """
    values = np.asarray(mip_yx)
    if (values.ndim != 2 or min(values.shape) < 2
            or not np.issubdtype(values.dtype, np.number)
            or np.iscomplexobj(values)):
        raise ValueError("mip_yx must be a real numeric 2-D array, rows=Y, columns=X")
    center = np.asarray(center_mm, dtype=float)
    space = np.asarray(space_mm, dtype=float)
    if center.shape != (3,) or not np.isfinite(center).all():
        raise ValueError("center_mm must contain three finite coordinates")
    if space.shape != (3,) or not np.isfinite(space).all() or np.any(space <= 0):
        raise ValueError("space_mm must contain three positive finite lengths")
    if min(space[:2]) <= 10:
        raise ValueError("XY FOV must exceed 10 mm to leave a valid search region")
    if not np.isfinite(values).all() or np.ptp(values.astype(float)) <= 0:
        raise ValueError("Invalid/constant XY MIP; no segmentation or rotation proposed")
    dx = space[0] / (values.shape[1] - 1)
    dy = space[1] / (values.shape[0] - 1)
    if not np.isclose(dx, dy, rtol=0.02, atol=1e-12):
        raise ValueError("Original segmentation requires approximately equal X/Y pixel spacing")
    if sigma_upper is not None and (not np.isfinite(sigma_upper) or sigma_upper < 3):
        raise ValueError("sigma_upper must be finite and >=3, or None to disable")
    result, mask, _, _ = segment(
        values, center=tuple(center), space=tuple(space),
        vessel_prior=vessel_prior, sigma_upper=sigma_upper)
    result["rotation_matrix_z"] = rotation(result["initial_z_rotation_deg"]).tolist()
    return result, mask
