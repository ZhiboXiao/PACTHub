#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>
#include <c10/cuda/CUDAGuard.h>
#include <c10/cuda/CUDAException.h>

#include <cuda.h>
#include <cuda_runtime.h>
#include <cmath>
#include <cstdint>

namespace {

struct GridGeometry {
    float x0, y0, z0;
    float dx, dy, dz;
    int nx, ny, nz;
};

struct AcousticParameters {
    int numSamples;
    float fsMHz;
    float predelaySamples;
    float soundSpeedMmPerUs;
};

// Straight-ray, two-region travel-time model used by the new ADPAT DualV
// reconstruction.  The unit normal points into region 1; signed distances
// >= 0 therefore use speed1, while signed distances < 0 use speed2.  This
// intentionally reproduces the supplied DualV program: it splits the direct
// source-receiver segment at a planar interface and does not bend the ray by
// Snell's law.
struct DualSpeedPlane {
    float speed1MmPerUs;
    float speed2MmPerUs;
    float p1x, p1y, p1z;
    float nx, ny, nz;
};

__device__ __forceinline__ void voxelPosition(
    size_t voxelIndex, const GridGeometry& grid,
    float& x, float& y, float& z)
{
    const int ix = static_cast<int>(
        voxelIndex % static_cast<size_t>(grid.nx));
    const size_t yzIndex = voxelIndex / static_cast<size_t>(grid.nx);
    const int iy = static_cast<int>(
        yzIndex % static_cast<size_t>(grid.ny));
    const int iz = static_cast<int>(
        yzIndex / static_cast<size_t>(grid.ny));
    x = fmaf(grid.dx, static_cast<float>(ix), grid.x0);
    y = fmaf(grid.dy, static_cast<float>(iy), grid.y0);
    z = fmaf(grid.dz, static_cast<float>(iz), grid.z0);
}

__device__ __forceinline__ bool sampleTerms(
    float distance, const AcousticParameters& acoustic,
    int& sample0, float& fraction)
{
    if (distance <= 0.0f) return false;
    const float sampleCoordinate =
        acoustic.fsMHz * distance / acoustic.soundSpeedMmPerUs -
        acoustic.predelaySamples - 1.0f;
    sample0 = static_cast<int>(floorf(sampleCoordinate));
    if (sample0 < 0 || sample0 + 1 >= acoustic.numSamples) return false;
    fraction = sampleCoordinate - static_cast<float>(sample0);
    return true;
}

__device__ __forceinline__ float planeSignedDistance(
    float x, float y, float z, const DualSpeedPlane& medium)
{
    return fmaf(
        x - medium.p1x, medium.nx,
        fmaf(y - medium.p1y, medium.ny, (z - medium.p1z) * medium.nz));
}

__device__ __forceinline__ bool dualSpeedSampleTerms(
    float px, float py, float pz,
    float sx, float sy, float sz,
    const AcousticParameters& acoustic,
    const DualSpeedPlane& medium,
    float& distance, int& sample0, float& fraction)
{
    const float vx = px - sx;
    const float vy = py - sy;
    const float vz = pz - sz;
    const float distanceSquared = fmaf(vx, vx, fmaf(vy, vy, vz * vz));
    if (distanceSquared <= 1.0e-12f) return false;
    distance = sqrtf(distanceSquared);

    float travelTimeUs;
    // Preserve the old single-speed expression exactly when the two speeds
    // are equal.  This is both a useful regression property and avoids a
    // needless plane-dependent roundoff difference.
    if (medium.speed1MmPerUs == medium.speed2MmPerUs) {
        travelTimeUs = distance / medium.speed1MmPerUs;
    } else {
        const float sourceSide = planeSignedDistance(px, py, pz, medium);
        const float receiverSide = planeSignedDistance(sx, sy, sz, medium);
        const bool sourceInRegion1 = sourceSide >= 0.0f;
        const bool receiverInRegion1 = receiverSide >= 0.0f;
        if (sourceInRegion1 == receiverInRegion1) {
            travelTimeUs = distance /
                (sourceInRegion1 ? medium.speed1MmPerUs
                                 : medium.speed2MmPerUs);
        } else {
            // For opposite signs, |S_p-S_s| = |S_p|+|S_s|.  The fraction
            // below is the source-to-interface fraction used by the supplied
            // ADPAT_DualV implementation.
            const float denominator = fabsf(sourceSide) + fabsf(receiverSide);
            if (denominator <= 1.0e-12f) return false;
            const float sourceFraction = fabsf(sourceSide) / denominator;
            const float sourceLength = distance * sourceFraction;
            const float receiverLength = distance - sourceLength;
            if (sourceInRegion1) {
                travelTimeUs = sourceLength / medium.speed1MmPerUs +
                               receiverLength / medium.speed2MmPerUs;
            } else {
                travelTimeUs = sourceLength / medium.speed2MmPerUs +
                               receiverLength / medium.speed1MmPerUs;
            }
        }
    }

    const float sampleCoordinate =
        acoustic.fsMHz * travelTimeUs - acoustic.predelaySamples - 1.0f;
    sample0 = static_cast<int>(floorf(sampleCoordinate));
    if (sample0 < 0 || sample0 + 1 >= acoustic.numSamples) return false;
    fraction = sampleCoordinate - static_cast<float>(sample0);
    return isfinite(fraction);
}

// Continuous spatial impulse response of a circular, non-focusing receiver.
//
// For a source point and a receiver disk, let z be the normal distance from
// the source to the receiver plane and b the distance between the projected
// source and disk centre.  On the receiver plane, the intersection of an
// isochronous sphere with radius r is a circle rho=sqrt(r^2-z^2).  The angle
// Phi covered by that circle inside the receiver disk gives
//
//   (1 / pi a^2) integral_disk delta(r-r') / r' dA = Phi(r) / (pi a^2).
//
// We integrate this expression against the same triangular time-sampling
// basis used by the legacy point-quadrature projector.  Thus the analytic
// forward and adjoint below are a matched pair and conserve the area-average
// 1/r response without introducing an empirical, space-invariant PSF.
constexpr float kPi = 3.14159265358979323846f;

struct AnalyticDiskTerms {
    float axialDistance;
    float lateralDistance;
    float uMin;
    float uMax;
    float uTransition;
};

__device__ __forceinline__ bool analyticDiskTerms(
    float px, float py, float pz,
    float sx, float sy, float sz,
    float radius, const AcousticParameters& acoustic,
    AnalyticDiskTerms& terms)
{
    const float sensorNormSquared = fmaf(sx, sx, fmaf(sy, sy, sz * sz));
    if (sensorNormSquared <= 1.0e-12f || radius <= 0.0f) return false;
    const float inverseSensorNorm = rsqrtf(sensorNormSquared);
    const float vx = px - sx;
    const float vy = py - sy;
    const float vz = pz - sz;
    const float axialSigned =
        (fmaf(vx, sx, fmaf(vy, sy, vz * sz))) * inverseSensorNorm;
    const float distanceSquared = fmaf(vx, vx, fmaf(vy, vy, vz * vz));
    const float axialSquared = axialSigned * axialSigned;
    const float lateralSquared = fmaxf(distanceSquared - axialSquared, 0.0f);
    const float lateral = sqrtf(lateralSquared);
    const float rhoMin = fmaxf(lateral - radius, 0.0f);
    const float rhoMax = lateral + radius;
    const float axial = fabsf(axialSigned);
    const float rMin = sqrtf(fmaf(rhoMin, rhoMin, axialSquared));
    const float rMax = sqrtf(fmaf(rhoMax, rhoMax, axialSquared));
    const float rhoTransition = fabsf(radius - lateral);
    const float rTransition =
        sqrtf(fmaf(rhoTransition, rhoTransition, axialSquared));
    const float samplesPerMm =
        acoustic.fsMHz / acoustic.soundSpeedMmPerUs;
    const float clockOffset = acoustic.predelaySamples + 1.0f;
    terms.axialDistance = axial;
    terms.lateralDistance = lateral;
    terms.uMin = samplesPerMm * rMin - clockOffset;
    terms.uMax = samplesPerMm * rMax - clockOffset;
    terms.uTransition = samplesPerMm * rTransition - clockOffset;
    return isfinite(terms.uMin) && isfinite(terms.uMax) &&
           terms.uMax >= terms.uMin;
}

__device__ __forceinline__ float diskAngularSpan(
    float rho, float lateral, float radius)
{
    constexpr float epsilon = 1.0e-6f;
    if (rho <= epsilon) return lateral <= radius ? 2.0f * kPi : 0.0f;
    if (lateral <= epsilon) return rho <= radius ? 2.0f * kPi : 0.0f;
    if (lateral + rho <= radius) return 2.0f * kPi;
    if (lateral >= radius + rho || rho >= radius + lateral) return 0.0f;
    const float cosine = fmaf(
        lateral, lateral,
        fmaf(rho, rho, -radius * radius)) / (2.0f * lateral * rho);
    return 2.0f * acosf(fminf(fmaxf(cosine, -1.0f), 1.0f));
}

__device__ __forceinline__ float analyticDiskIntegrand(
    float u, int sampleIndex, const AnalyticDiskTerms& terms,
    float radius, const AcousticParameters& acoustic)
{
    const float r =
        (u + acoustic.predelaySamples + 1.0f) *
        acoustic.soundSpeedMmPerUs / acoustic.fsMHz;
    const float rhoSquared =
        fmaxf(r * r - terms.axialDistance * terms.axialDistance, 0.0f);
    const float rho = sqrtf(rhoSquared);
    const float triangle =
        fmaxf(1.0f - fabsf(u - static_cast<float>(sampleIndex)), 0.0f);
    return diskAngularSpan(rho, terms.lateralDistance, radius) * triangle;
}

__device__ __forceinline__ float integrateAnalyticDiskInterval(
    float lower, float upper, int sampleIndex,
    const AnalyticDiskTerms& terms, float radius,
    const AcousticParameters& acoustic)
{
    if (upper <= lower) return 0.0f;
    const float midpoint = 0.5f * (lower + upper);
    const float halfWidth = 0.5f * (upper - lower);
    constexpr float nodeOuter = 0.8611363115940526f;
    constexpr float nodeInner = 0.3399810435848563f;
    constexpr float weightOuter = 0.3478548451374538f;
    constexpr float weightInner = 0.6521451548625461f;
    const float outer =
        analyticDiskIntegrand(
            midpoint - halfWidth * nodeOuter, sampleIndex,
            terms, radius, acoustic) +
        analyticDiskIntegrand(
            midpoint + halfWidth * nodeOuter, sampleIndex,
            terms, radius, acoustic);
    const float inner =
        analyticDiskIntegrand(
            midpoint - halfWidth * nodeInner, sampleIndex,
            terms, radius, acoustic) +
        analyticDiskIntegrand(
            midpoint + halfWidth * nodeInner, sampleIndex,
            terms, radius, acoustic);
    return halfWidth * (weightOuter * outer + weightInner * inner);
}

__device__ __forceinline__ float analyticDiskSampleWeight(
    int sampleIndex, const AnalyticDiskTerms& terms,
    float radius, const AcousticParameters& acoustic)
{
    const float sample = static_cast<float>(sampleIndex);
    const float lower = fmaxf(terms.uMin, sample - 1.0f);
    const float upper = fminf(terms.uMax, sample + 1.0f);
    if (upper <= lower) return 0.0f;

    // Split at the triangular-basis cusp and at the full/partial disk-overlap
    // transition.  Four-point Gauss-Legendre is then applied only to smooth
    // pieces, including the sub-sample-width on-axis SIR.
    float boundaries[4];
    int count = 0;
    boundaries[count++] = lower;
    if (sample > lower && sample < upper) boundaries[count++] = sample;
    if (terms.uTransition > lower && terms.uTransition < upper)
        boundaries[count++] = terms.uTransition;
    boundaries[count++] = upper;
    for (int i = 1; i < count; ++i) {
        const float value = boundaries[i];
        int j = i - 1;
        while (j >= 0 && boundaries[j] > value) {
            boundaries[j + 1] = boundaries[j];
            --j;
        }
        boundaries[j + 1] = value;
    }
    float integral = 0.0f;
    for (int i = 0; i + 1 < count; ++i) {
        integral += integrateAnalyticDiskInterval(
            boundaries[i], boundaries[i + 1], sampleIndex,
            terms, radius, acoustic);
    }
    const float drDu = acoustic.soundSpeedMmPerUs / acoustic.fsMHz;
    return integral * drDu / (kPi * radius * radius);
}

__device__ __forceinline__ void analyticDiskSampleBounds(
    const AnalyticDiskTerms& terms, const AcousticParameters& acoustic,
    int& firstSample, int& lastSample)
{
    firstSample = max(0, static_cast<int>(ceilf(terms.uMin - 1.0f)));
    lastSample = min(
        acoustic.numSamples - 1,
        static_cast<int>(floorf(terms.uMax + 1.0f)));
}

__global__ void analyticDiskForwardKernel(
    const float* __restrict__ volume,
    const float* __restrict__ sensors,
    float* __restrict__ sinogram,
    size_t numVoxels, int numSensors, float radius,
    GridGeometry grid, AcousticParameters acoustic)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (voxelIndex >= numVoxels || sensorIndex >= numSensors) return;
    const float voxelValue = volume[voxelIndex];
    if (voxelValue == 0.0f) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    AnalyticDiskTerms terms;
    if (!analyticDiskTerms(
            px, py, pz,
            sensors[sensorIndex], sensors[sensorIndex + numSensors],
            sensors[sensorIndex + 2 * numSensors], radius, acoustic, terms))
        return;
    int firstSample, lastSample;
    analyticDiskSampleBounds(terms, acoustic, firstSample, lastSample);
    for (int sample = firstSample; sample <= lastSample; ++sample) {
        const float weight =
            analyticDiskSampleWeight(sample, terms, radius, acoustic);
        if (weight == 0.0f) continue;
        const size_t index =
            static_cast<size_t>(sample) * numSensors + sensorIndex;
        atomicAdd(&sinogram[index], voxelValue * weight);
    }
}

__global__ void analyticDiskAdjointWarpKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sensors,
    float* __restrict__ volume,
    size_t numVoxels, int numSensors, float radius,
    GridGeometry grid, AcousticParameters acoustic)
{
    constexpr unsigned int warpSizeValue = 32;
    const unsigned int lane = threadIdx.x & (warpSizeValue - 1);
    const unsigned int warpInBlock = threadIdx.x / warpSizeValue;
    const unsigned int warpsPerBlock = blockDim.x / warpSizeValue;
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * warpsPerBlock + warpInBlock;
    if (voxelIndex >= numVoxels) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    float value = 0.0f;
    for (int sensorIndex = static_cast<int>(lane);
         sensorIndex < numSensors;
         sensorIndex += static_cast<int>(warpSizeValue)) {
        AnalyticDiskTerms terms;
        if (!analyticDiskTerms(
                px, py, pz,
                sensors[sensorIndex], sensors[sensorIndex + numSensors],
                sensors[sensorIndex + 2 * numSensors], radius,
                acoustic, terms))
            continue;
        int firstSample, lastSample;
        analyticDiskSampleBounds(terms, acoustic, firstSample, lastSample);
        for (int sample = firstSample; sample <= lastSample; ++sample) {
            const float weight =
                analyticDiskSampleWeight(sample, terms, radius, acoustic);
            const size_t index =
                static_cast<size_t>(sample) * numSensors + sensorIndex;
            value = fmaf(weight, sinogram[index], value);
        }
    }
    constexpr unsigned int fullWarpMask = 0xffffffffu;
    for (int offset = 16; offset > 0; offset >>= 1)
        value += __shfl_down_sync(fullWarpMask, value, offset);
    if (lane == 0) volume[voxelIndex] = value;
}

__global__ void analyticSparseDiskForwardKernel(
    const float* __restrict__ sourcePositions,
    const float* __restrict__ sourceAmplitudes,
    const float* __restrict__ sensors,
    float* __restrict__ sinogram,
    size_t numSources, int numSensors, float radius,
    AcousticParameters acoustic)
{
    const size_t sourceIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (sourceIndex >= numSources || sensorIndex >= numSensors) return;
    const float amplitude = sourceAmplitudes[sourceIndex];
    if (amplitude == 0.0f) return;
    AnalyticDiskTerms terms;
    if (!analyticDiskTerms(
            sourcePositions[sourceIndex],
            sourcePositions[sourceIndex + numSources],
            sourcePositions[sourceIndex + 2 * numSources],
            sensors[sensorIndex], sensors[sensorIndex + numSensors],
            sensors[sensorIndex + 2 * numSensors], radius, acoustic, terms))
        return;
    int firstSample, lastSample;
    analyticDiskSampleBounds(terms, acoustic, firstSample, lastSample);
    for (int sample = firstSample; sample <= lastSample; ++sample) {
        const float weight =
            analyticDiskSampleWeight(sample, terms, radius, acoustic);
        if (weight == 0.0f) continue;
        const size_t index =
            static_cast<size_t>(sample) * numSensors + sensorIndex;
        atomicAdd(&sinogram[index], amplitude * weight);
    }
}

__global__ void analyticSparseDiskAdjointKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sourcePositions,
    const float* __restrict__ sensors,
    float* __restrict__ sourceGradient,
    size_t numSources, int numSensors, float radius,
    AcousticParameters acoustic)
{
    const size_t sourceIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (sourceIndex >= numSources) return;
    const float px = sourcePositions[sourceIndex];
    const float py = sourcePositions[sourceIndex + numSources];
    const float pz = sourcePositions[sourceIndex + 2 * numSources];
    float value = 0.0f;
    for (int sensorIndex = 0; sensorIndex < numSensors; ++sensorIndex) {
        AnalyticDiskTerms terms;
        if (!analyticDiskTerms(
                px, py, pz,
                sensors[sensorIndex], sensors[sensorIndex + numSensors],
                sensors[sensorIndex + 2 * numSensors], radius,
                acoustic, terms))
            continue;
        int firstSample, lastSample;
        analyticDiskSampleBounds(terms, acoustic, firstSample, lastSample);
        for (int sample = firstSample; sample <= lastSample; ++sample) {
            const float weight =
                analyticDiskSampleWeight(sample, terms, radius, acoustic);
            const size_t index =
                static_cast<size_t>(sample) * numSensors + sensorIndex;
            value = fmaf(weight, sinogram[index], value);
        }
    }
    sourceGradient[sourceIndex] = value;
}

__global__ void diskForwardKernel(
    const float* __restrict__ volume,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ sinogram,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (voxelIndex >= numVoxels || sensorIndex >= numSensors) return;

    const float voxelValue = volume[voxelIndex];
    if (voxelValue == 0.0f) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const float sx = sensors[sensorIndex];
    const float sy = sensors[sensorIndex + numSensors];
    const float sz = sensors[sensorIndex + 2 * numSensors];
    const float vx = px - sx;
    const float vy = py - sy;
    const float vz = pz - sz;
    const float centerDistanceSquared =
        fmaf(vx, vx, fmaf(vy, vy, vz * vz));
    if (centerDistanceSquared <= 1.0e-12f) return;
    const float centerDistance = sqrtf(centerDistanceSquared);
    const int expanded = numSensors * numSubpoints;

    for (int q = 0; q < numSubpoints; ++q) {
        const int oi = sensorIndex + q * numSensors;
        const float ux = offsets[oi];
        const float uy = offsets[oi + expanded];
        const float uz = offsets[oi + 2 * expanded];
        const float projection = fmaf(vx, ux, fmaf(vy, uy, vz * uz));
        const float offsetSquared = fmaf(ux, ux, fmaf(uy, uy, uz * uz));
        const float distanceSquared = fmaf(
            -2.0f, projection,
            fmaf(centerDistance, centerDistance, offsetSquared));
        const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
        int sample0;
        float fraction;
        if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
        const float value = voxelValue * weights[q] / distance;
        const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                              static_cast<size_t>(sensorIndex);
        atomicAdd(&sinogram[index0], value * (1.0f - fraction));
        atomicAdd(&sinogram[index0 + numSensors], value * fraction);
    }
}

__global__ void diskAdjointKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ volume,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (voxelIndex >= numVoxels) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const int expanded = numSensors * numSubpoints;
    float value = 0.0f;
    for (int sensorIndex = 0; sensorIndex < numSensors; ++sensorIndex) {
        const float vx = px - sensors[sensorIndex];
        const float vy = py - sensors[sensorIndex + numSensors];
        const float vz = pz - sensors[sensorIndex + 2 * numSensors];
        const float centerDistanceSquared =
            fmaf(vx, vx, fmaf(vy, vy, vz * vz));
        if (centerDistanceSquared <= 1.0e-12f) continue;
        const float centerDistance = sqrtf(centerDistanceSquared);
        for (int q = 0; q < numSubpoints; ++q) {
            const int oi = sensorIndex + q * numSensors;
            const float ux = offsets[oi];
            const float uy = offsets[oi + expanded];
            const float uz = offsets[oi + 2 * expanded];
            const float projection = fmaf(vx, ux, fmaf(vy, uy, vz * uz));
            const float offsetSquared =
                fmaf(ux, ux, fmaf(uy, uy, uz * uz));
            const float distanceSquared = fmaf(
                -2.0f, projection,
                fmaf(centerDistance, centerDistance, offsetSquared));
            const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
            int sample0;
            float fraction;
            if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
            const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                                  static_cast<size_t>(sensorIndex);
            const float interpolated =
                (1.0f - fraction) * sinogram[index0] +
                fraction * sinogram[index0 + numSensors];
            value += weights[q] * interpolated / distance;
        }
    }
    volume[voxelIndex] = value;
}

// Numerically equivalent disk adjoint with one CUDA warp assigned to each
// voxel.  The legacy kernel above assigns one thread to a voxel and makes
// that thread traverse all sensors serially.  Here each lane traverses
// sensorIndex = lane, lane + 32, ... and the warp reduces the 32 partial
// sums.  Geometry, SIR quadrature, interpolation and precision are
// unchanged; only the parallel reduction order differs.
__global__ void diskAdjointWarpKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ volume,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic)
{
    constexpr unsigned int warpSizeValue = 32;
    const unsigned int lane = threadIdx.x & (warpSizeValue - 1);
    const unsigned int warpInBlock = threadIdx.x / warpSizeValue;
    const unsigned int warpsPerBlock = blockDim.x / warpSizeValue;
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * warpsPerBlock + warpInBlock;
    if (voxelIndex >= numVoxels) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const int expanded = numSensors * numSubpoints;
    float value = 0.0f;

    for (int sensorIndex = static_cast<int>(lane);
         sensorIndex < numSensors;
         sensorIndex += static_cast<int>(warpSizeValue)) {
        const float vx = px - sensors[sensorIndex];
        const float vy = py - sensors[sensorIndex + numSensors];
        const float vz = pz - sensors[sensorIndex + 2 * numSensors];
        const float centerDistanceSquared =
            fmaf(vx, vx, fmaf(vy, vy, vz * vz));
        if (centerDistanceSquared <= 1.0e-12f) continue;
        const float centerDistance = sqrtf(centerDistanceSquared);

        for (int q = 0; q < numSubpoints; ++q) {
            const int oi = sensorIndex + q * numSensors;
            const float ux = offsets[oi];
            const float uy = offsets[oi + expanded];
            const float uz = offsets[oi + 2 * expanded];
            const float projection = fmaf(vx, ux, fmaf(vy, uy, vz * uz));
            const float offsetSquared =
                fmaf(ux, ux, fmaf(uy, uy, uz * uz));
            const float distanceSquared = fmaf(
                -2.0f, projection,
                fmaf(centerDistance, centerDistance, offsetSquared));
            const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
            int sample0;
            float fraction;
            if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
            const size_t index0 =
                static_cast<size_t>(sample0) * numSensors +
                static_cast<size_t>(sensorIndex);
            const float interpolated =
                (1.0f - fraction) * sinogram[index0] +
                fraction * sinogram[index0 + numSensors];
            value += weights[q] * interpolated / distance;
        }
    }

    constexpr unsigned int fullWarpMask = 0xffffffffu;
    for (int offset = 16; offset > 0; offset >>= 1) {
        value += __shfl_down_sync(fullWarpMask, value, offset);
    }
    if (lane == 0) volume[voxelIndex] = value;
}

__global__ void dualSpeedDiskForwardKernel(
    const float* __restrict__ volume,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ sinogram,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic, DualSpeedPlane medium)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (voxelIndex >= numVoxels || sensorIndex >= numSensors) return;

    const float voxelValue = volume[voxelIndex];
    if (voxelValue == 0.0f) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const float centerX = sensors[sensorIndex];
    const float centerY = sensors[sensorIndex + numSensors];
    const float centerZ = sensors[sensorIndex + 2 * numSensors];
    const int expanded = numSensors * numSubpoints;

    for (int q = 0; q < numSubpoints; ++q) {
        const int oi = sensorIndex + q * numSensors;
        const float sx = centerX + offsets[oi];
        const float sy = centerY + offsets[oi + expanded];
        const float sz = centerZ + offsets[oi + 2 * expanded];
        float distance, fraction;
        int sample0;
        if (!dualSpeedSampleTerms(
                px, py, pz, sx, sy, sz, acoustic, medium,
                distance, sample0, fraction))
            continue;
        const float value = voxelValue * weights[q] / distance;
        const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                              static_cast<size_t>(sensorIndex);
        atomicAdd(&sinogram[index0], value * (1.0f - fraction));
        atomicAdd(&sinogram[index0 + numSensors], value * fraction);
    }
}

// One warp per voxel, matching the dual-speed forward weights exactly.
// Each lane traverses a disjoint subset of sensors and the warp reduction is
// only an execution optimization; it does not alter the modeled rays.
__global__ void dualSpeedDiskAdjointWarpKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ volume,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic, DualSpeedPlane medium)
{
    constexpr unsigned int warpSizeValue = 32;
    const unsigned int lane = threadIdx.x & (warpSizeValue - 1);
    const unsigned int warpInBlock = threadIdx.x / warpSizeValue;
    const unsigned int warpsPerBlock = blockDim.x / warpSizeValue;
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * warpsPerBlock + warpInBlock;
    if (voxelIndex >= numVoxels) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const int expanded = numSensors * numSubpoints;
    float value = 0.0f;
    for (int sensorIndex = static_cast<int>(lane);
         sensorIndex < numSensors;
         sensorIndex += static_cast<int>(warpSizeValue)) {
        const float centerX = sensors[sensorIndex];
        const float centerY = sensors[sensorIndex + numSensors];
        const float centerZ = sensors[sensorIndex + 2 * numSensors];
        for (int q = 0; q < numSubpoints; ++q) {
            const int oi = sensorIndex + q * numSensors;
            const float sx = centerX + offsets[oi];
            const float sy = centerY + offsets[oi + expanded];
            const float sz = centerZ + offsets[oi + 2 * expanded];
            float distance, fraction;
            int sample0;
            if (!dualSpeedSampleTerms(
                    px, py, pz, sx, sy, sz, acoustic, medium,
                    distance, sample0, fraction))
                continue;
            const size_t index0 =
                static_cast<size_t>(sample0) * numSensors +
                static_cast<size_t>(sensorIndex);
            const float interpolated =
                (1.0f - fraction) * sinogram[index0] +
                fraction * sinogram[index0 + numSensors];
            value += weights[q] * interpolated / distance;
        }
    }

    constexpr unsigned int fullWarpMask = 0xffffffffu;
    for (int offset = 16; offset > 0; offset >>= 1)
        value += __shfl_down_sync(fullWarpMask, value, offset);
    if (lane == 0) volume[voxelIndex] = value;
}

// Exact geometry using precomputed absolute sub-receiver coordinates
// (sensor centre + disk quadrature offset).  This removes the redundant
// centre-distance/projection expansion from the Q-loop without dropping
// any quadrature point or changing the physical Euclidean distance.
__global__ void diskForwardPrecomputedKernel(
    const float* __restrict__ volume,
    const float* __restrict__ subpointPositions,
    const float* __restrict__ weights,
    float* __restrict__ sinogram,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (voxelIndex >= numVoxels || sensorIndex >= numSensors) return;

    const float voxelValue = volume[voxelIndex];
    if (voxelValue == 0.0f) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const int expanded = numSensors * numSubpoints;
    for (int q = 0; q < numSubpoints; ++q) {
        const int qi = sensorIndex + q * numSensors;
        const float vx = px - subpointPositions[qi];
        const float vy = py - subpointPositions[qi + expanded];
        const float vz = pz - subpointPositions[qi + 2 * expanded];
        const float distanceSquared = fmaf(vx, vx, fmaf(vy, vy, vz * vz));
        const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
        int sample0;
        float fraction;
        if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
        const float value = voxelValue * weights[q] / distance;
        const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                              static_cast<size_t>(sensorIndex);
        atomicAdd(&sinogram[index0], value * (1.0f - fraction));
        atomicAdd(&sinogram[index0 + numSensors], value * fraction);
    }
}

__global__ void diskAdjointPrecomputedKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ subpointPositions,
    const float* __restrict__ weights,
    float* __restrict__ volume,
    size_t numVoxels, int numSensors, int numSubpoints,
    GridGeometry grid, AcousticParameters acoustic)
{
    const size_t voxelIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (voxelIndex >= numVoxels) return;

    float px, py, pz;
    voxelPosition(voxelIndex, grid, px, py, pz);
    const int expanded = numSensors * numSubpoints;
    float value = 0.0f;
    for (int sensorIndex = 0; sensorIndex < numSensors; ++sensorIndex) {
        for (int q = 0; q < numSubpoints; ++q) {
            const int qi = sensorIndex + q * numSensors;
            const float vx = px - subpointPositions[qi];
            const float vy = py - subpointPositions[qi + expanded];
            const float vz = pz - subpointPositions[qi + 2 * expanded];
            const float distanceSquared =
                fmaf(vx, vx, fmaf(vy, vy, vz * vz));
            const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
            int sample0;
            float fraction;
            if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
            const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                                  static_cast<size_t>(sensorIndex);
            const float interpolated =
                (1.0f - fraction) * sinogram[index0] +
                fraction * sinogram[index0 + numSensors];
            value += weights[q] * interpolated / distance;
        }
    }
    volume[voxelIndex] = value;
}

__global__ void sparseDiskForwardKernel(
    const float* __restrict__ sourcePositions,
    const float* __restrict__ sourceAmplitudes,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ sinogram,
    size_t numSources, int numSensors, int numSubpoints,
    AcousticParameters acoustic)
{
    const size_t sourceIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const int sensorIndex =
        static_cast<int>(blockIdx.y) * blockDim.y + threadIdx.y;
    if (sourceIndex >= numSources || sensorIndex >= numSensors) return;

    const float sourceAmplitude = sourceAmplitudes[sourceIndex];
    if (sourceAmplitude == 0.0f) return;
    const float px = sourcePositions[sourceIndex];
    const float py = sourcePositions[sourceIndex + numSources];
    const float pz = sourcePositions[sourceIndex + 2 * numSources];
    const float vx = px - sensors[sensorIndex];
    const float vy = py - sensors[sensorIndex + numSensors];
    const float vz = pz - sensors[sensorIndex + 2 * numSensors];
    const float centerDistanceSquared =
        fmaf(vx, vx, fmaf(vy, vy, vz * vz));
    if (centerDistanceSquared <= 1.0e-12f) return;
    const float centerDistance = sqrtf(centerDistanceSquared);
    const int expanded = numSensors * numSubpoints;

    for (int q = 0; q < numSubpoints; ++q) {
        const int oi = sensorIndex + q * numSensors;
        const float ux = offsets[oi];
        const float uy = offsets[oi + expanded];
        const float uz = offsets[oi + 2 * expanded];
        const float projection = fmaf(vx, ux, fmaf(vy, uy, vz * uz));
        const float offsetSquared = fmaf(ux, ux, fmaf(uy, uy, uz * uz));
        const float distanceSquared = fmaf(
            -2.0f, projection,
            fmaf(centerDistance, centerDistance, offsetSquared));
        const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
        int sample0;
        float fraction;
        if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
        const float value = sourceAmplitude * weights[q] / distance;
        const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                              static_cast<size_t>(sensorIndex);
        atomicAdd(&sinogram[index0], value * (1.0f - fraction));
        atomicAdd(&sinogram[index0 + numSensors], value * fraction);
    }
}

__global__ void sparseDiskAdjointKernel(
    const float* __restrict__ sinogram,
    const float* __restrict__ sourcePositions,
    const float* __restrict__ sensors,
    const float* __restrict__ offsets,
    const float* __restrict__ weights,
    float* __restrict__ sourceGradient,
    size_t numSources, int numSensors, int numSubpoints,
    AcousticParameters acoustic)
{
    const size_t sourceIndex =
        static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (sourceIndex >= numSources) return;

    const float px = sourcePositions[sourceIndex];
    const float py = sourcePositions[sourceIndex + numSources];
    const float pz = sourcePositions[sourceIndex + 2 * numSources];
    const int expanded = numSensors * numSubpoints;
    float value = 0.0f;
    for (int sensorIndex = 0; sensorIndex < numSensors; ++sensorIndex) {
        const float vx = px - sensors[sensorIndex];
        const float vy = py - sensors[sensorIndex + numSensors];
        const float vz = pz - sensors[sensorIndex + 2 * numSensors];
        const float centerDistanceSquared =
            fmaf(vx, vx, fmaf(vy, vy, vz * vz));
        if (centerDistanceSquared <= 1.0e-12f) continue;
        const float centerDistance = sqrtf(centerDistanceSquared);
        for (int q = 0; q < numSubpoints; ++q) {
            const int oi = sensorIndex + q * numSensors;
            const float ux = offsets[oi];
            const float uy = offsets[oi + expanded];
            const float uz = offsets[oi + 2 * expanded];
            const float projection = fmaf(vx, ux, fmaf(vy, uy, vz * uz));
            const float offsetSquared =
                fmaf(ux, ux, fmaf(uy, uy, uz * uz));
            const float distanceSquared = fmaf(
                -2.0f, projection,
                fmaf(centerDistance, centerDistance, offsetSquared));
            const float distance = sqrtf(fmaxf(distanceSquared, 1.0e-12f));
            int sample0;
            float fraction;
            if (!sampleTerms(distance, acoustic, sample0, fraction)) continue;
            const size_t index0 = static_cast<size_t>(sample0) * numSensors +
                                  static_cast<size_t>(sensorIndex);
            const float interpolated =
                (1.0f - fraction) * sinogram[index0] +
                fraction * sinogram[index0 + numSensors];
            value += weights[q] * interpolated / distance;
        }
    }
    sourceGradient[sourceIndex] = value;
}

void checkTensor(const torch::Tensor& tensor, const char* name) {
    TORCH_CHECK(tensor.is_cuda(), name, " must be a CUDA tensor");
    TORCH_CHECK(tensor.scalar_type() == torch::kFloat32,
                name, " must be float32");
    TORCH_CHECK(tensor.is_contiguous(), name, " must be contiguous");
}

GridGeometry makeGrid(
    const torch::Tensor& volume,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    TORCH_CHECK(volume.dim() == 3, "volume must have shape [nz,ny,nx]");
    GridGeometry grid;
    grid.nz = static_cast<int>(volume.size(0));
    grid.ny = static_cast<int>(volume.size(1));
    grid.nx = static_cast<int>(volume.size(2));
    grid.x0 = static_cast<float>(x0);
    grid.y0 = static_cast<float>(y0);
    grid.z0 = static_cast<float>(z0);
    grid.dx = static_cast<float>(dx);
    grid.dy = static_cast<float>(dy);
    grid.dz = static_cast<float>(dz);
    TORCH_CHECK(grid.nx > 0 && grid.ny > 0 && grid.nz > 0,
                "grid dimensions must be positive");
    return grid;
}

AcousticParameters makeAcoustic(
    int64_t numSamples, double fsMHz,
    double predelaySamples, double soundSpeedMps)
{
    TORCH_CHECK(numSamples >= 2 && fsMHz > 0.0 && soundSpeedMps > 0.0,
                "invalid acoustic parameters");
    AcousticParameters acoustic;
    acoustic.numSamples = static_cast<int>(numSamples);
    acoustic.fsMHz = static_cast<float>(fsMHz);
    acoustic.predelaySamples = static_cast<float>(predelaySamples);
    acoustic.soundSpeedMmPerUs = static_cast<float>(soundSpeedMps * 1.0e-3);
    return acoustic;
}

DualSpeedPlane makeDualSpeedPlane(
    double speed1Mps, double speed2Mps,
    double p1x, double p1y, double p1z,
    double nx, double ny, double nz)
{
    TORCH_CHECK(speed1Mps > 0.0 && speed2Mps > 0.0,
                "dual sound speeds must be positive");
    const double normalNorm = std::sqrt(nx * nx + ny * ny + nz * nz);
    TORCH_CHECK(std::isfinite(normalNorm) && normalNorm > 0.0,
                "dual-speed plane normal must be finite and nonzero");
    DualSpeedPlane medium;
    medium.speed1MmPerUs = static_cast<float>(speed1Mps * 1.0e-3);
    medium.speed2MmPerUs = static_cast<float>(speed2Mps * 1.0e-3);
    medium.p1x = static_cast<float>(p1x);
    medium.p1y = static_cast<float>(p1y);
    medium.p1z = static_cast<float>(p1z);
    medium.nx = static_cast<float>(nx / normalNorm);
    medium.ny = static_cast<float>(ny / normalNorm);
    medium.nz = static_cast<float>(nz / normalNorm);
    return medium;
}

void checkGeometry(
    const torch::Tensor& sensors,
    const torch::Tensor& offsets,
    const torch::Tensor& weights)
{
    checkTensor(sensors, "sensors");
    checkTensor(offsets, "offsets");
    checkTensor(weights, "weights");
    TORCH_CHECK(sensors.dim() == 2 && sensors.size(0) == 3,
                "sensors must have shape [3,N]");
    TORCH_CHECK(offsets.dim() == 3 && offsets.size(0) == 3 &&
                offsets.size(2) == sensors.size(1),
                "offsets must have shape [3,Q,N]");
    TORCH_CHECK(weights.dim() == 1 && weights.size(0) == offsets.size(1),
                "weights must have shape [Q]");
    TORCH_CHECK(sensors.device() == offsets.device() &&
                sensors.device() == weights.device(),
                "geometry tensors must be on one CUDA device");
}

void checkSubpointGeometry(
    const torch::Tensor& subpointPositions,
    const torch::Tensor& weights)
{
    checkTensor(subpointPositions, "subpoint_positions");
    checkTensor(weights, "weights");
    TORCH_CHECK(subpointPositions.dim() == 3 &&
                subpointPositions.size(0) == 3,
                "subpoint_positions must have shape [3,Q,N]");
    TORCH_CHECK(weights.dim() == 1 &&
                weights.size(0) == subpointPositions.size(1),
                "weights must have shape [Q]");
    TORCH_CHECK(subpointPositions.device() == weights.device(),
                "subpoint positions and weights must share a CUDA device");
}

void checkSparseSources(
    const torch::Tensor& sourcePositions,
    const torch::Tensor& sourceAmplitudes)
{
    checkTensor(sourcePositions, "source_positions");
    checkTensor(sourceAmplitudes, "source_amplitudes");
    TORCH_CHECK(sourcePositions.dim() == 2 && sourcePositions.size(0) == 3,
                "source_positions must have shape [3,K]");
    TORCH_CHECK(sourceAmplitudes.dim() == 1 &&
                sourceAmplitudes.size(0) == sourcePositions.size(1),
                "source_amplitudes must have shape [K]");
    TORCH_CHECK(sourcePositions.device() == sourceAmplitudes.device(),
                "sparse source tensors must share a CUDA device");
}

void checkSensors(const torch::Tensor& sensors) {
    checkTensor(sensors, "sensors");
    TORCH_CHECK(sensors.dim() == 2 && sensors.size(0) == 3,
                "sensors must have shape [3,N]");
}

}  // namespace

torch::Tensor disk_forward(
    torch::Tensor volume, torch::Tensor sensors,
    torch::Tensor offsets, torch::Tensor weights,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(volume, "volume");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(volume.device() == sensors.device(),
                "volume and geometry must share a CUDA device");
    const auto grid = makeGrid(volume, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, soundSpeedMps);
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));
    const size_t numVoxels = static_cast<size_t>(volume.numel());

    c10::cuda::CUDAGuard guard(volume.device());
    auto output = torch::zeros({numSamples, numSensors}, volume.options());
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numVoxels + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        volume.get_device()).stream();
    diskForwardKernel<<<blocks, threads, 0, stream>>>(
        volume.data_ptr<float>(), sensors.data_ptr<float>(),
        offsets.data_ptr<float>(), weights.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors, numSubpoints,
        grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor disk_adjoint(
    torch::Tensor sinogram, torch::Tensor sensors,
    torch::Tensor offsets, torch::Tensor weights,
    int64_t nx, int64_t ny, int64_t nz,
    double fsMHz, double predelaySamples, double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(sinogram, "sinogram");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device(),
                "sinogram and geometry must share a CUDA device");

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty({nz, ny, nx}, sinogram.options());
    const auto grid = makeGrid(output, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));
    const size_t numVoxels = static_cast<size_t>(output.numel());
    constexpr unsigned int threads = 256;
    const unsigned int blocks = static_cast<unsigned int>(
        (numVoxels + threads - 1) / threads);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    diskAdjointKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sensors.data_ptr<float>(),
        offsets.data_ptr<float>(), weights.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors, numSubpoints,
        grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor disk_adjoint_warp(
    torch::Tensor sinogram, torch::Tensor sensors,
    torch::Tensor offsets, torch::Tensor weights,
    int64_t nx, int64_t ny, int64_t nz,
    double fsMHz, double predelaySamples, double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(sinogram, "sinogram");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device(),
                "sinogram and geometry must share a CUDA device");

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty({nz, ny, nx}, sinogram.options());
    const auto grid = makeGrid(output, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));
    const size_t numVoxels = static_cast<size_t>(output.numel());
    constexpr unsigned int threads = 256;
    constexpr unsigned int warpsPerBlock = threads / 32;
    const unsigned int blocks = static_cast<unsigned int>(
        (numVoxels + warpsPerBlock - 1) / warpsPerBlock);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    diskAdjointWarpKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sensors.data_ptr<float>(),
        offsets.data_ptr<float>(), weights.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors, numSubpoints,
        grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor dual_speed_disk_forward(
    torch::Tensor volume, torch::Tensor sensors,
    torch::Tensor offsets, torch::Tensor weights,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double speed1Mps, double speed2Mps,
    double p1x, double p1y, double p1z,
    double normalX, double normalY, double normalZ,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(volume, "volume");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(volume.device() == sensors.device(),
                "volume and geometry must share a CUDA device");
    const auto grid = makeGrid(volume, x0, y0, z0, dx, dy, dz);
    // The scalar sound speed is unused by the dual-speed kernel.  Keeping a
    // valid value in AcousticParameters preserves the common clock fields.
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, speed1Mps);
    const auto medium = makeDualSpeedPlane(
        speed1Mps, speed2Mps, p1x, p1y, p1z,
        normalX, normalY, normalZ);
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));
    const size_t numVoxels = static_cast<size_t>(volume.numel());

    c10::cuda::CUDAGuard guard(volume.device());
    auto output = torch::zeros({numSamples, numSensors}, volume.options());
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numVoxels + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        volume.get_device()).stream();
    dualSpeedDiskForwardKernel<<<blocks, threads, 0, stream>>>(
        volume.data_ptr<float>(), sensors.data_ptr<float>(),
        offsets.data_ptr<float>(), weights.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors, numSubpoints,
        grid, acoustic, medium);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor dual_speed_disk_adjoint(
    torch::Tensor sinogram, torch::Tensor sensors,
    torch::Tensor offsets, torch::Tensor weights,
    int64_t nx, int64_t ny, int64_t nz,
    double fsMHz, double predelaySamples,
    double speed1Mps, double speed2Mps,
    double p1x, double p1y, double p1z,
    double normalX, double normalY, double normalZ,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(sinogram, "sinogram");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device(),
                "sinogram and geometry must share a CUDA device");

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty({nz, ny, nx}, sinogram.options());
    const auto grid = makeGrid(output, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, speed1Mps);
    const auto medium = makeDualSpeedPlane(
        speed1Mps, speed2Mps, p1x, p1y, p1z,
        normalX, normalY, normalZ);
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));
    const size_t numVoxels = static_cast<size_t>(output.numel());
    constexpr unsigned int threads = 256;
    constexpr unsigned int warpsPerBlock = threads / 32;
    const unsigned int blocks = static_cast<unsigned int>(
        (numVoxels + warpsPerBlock - 1) / warpsPerBlock);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    dualSpeedDiskAdjointWarpKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sensors.data_ptr<float>(),
        offsets.data_ptr<float>(), weights.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors, numSubpoints,
        grid, acoustic, medium);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor disk_forward_precomputed(
    torch::Tensor volume, torch::Tensor subpointPositions,
    torch::Tensor weights,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(volume, "volume");
    checkSubpointGeometry(subpointPositions, weights);
    TORCH_CHECK(volume.device() == subpointPositions.device(),
                "volume and subpoint positions must share a CUDA device");
    const auto grid = makeGrid(volume, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, soundSpeedMps);
    const int numSubpoints = static_cast<int>(subpointPositions.size(1));
    const int numSensors = static_cast<int>(subpointPositions.size(2));
    const size_t numVoxels = static_cast<size_t>(volume.numel());

    c10::cuda::CUDAGuard guard(volume.device());
    auto output = torch::zeros({numSamples, numSensors}, volume.options());
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numVoxels + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        volume.get_device()).stream();
    diskForwardPrecomputedKernel<<<blocks, threads, 0, stream>>>(
        volume.data_ptr<float>(), subpointPositions.data_ptr<float>(),
        weights.data_ptr<float>(), output.data_ptr<float>(),
        numVoxels, numSensors, numSubpoints, grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor disk_adjoint_precomputed(
    torch::Tensor sinogram, torch::Tensor subpointPositions,
    torch::Tensor weights,
    int64_t nx, int64_t ny, int64_t nz,
    double fsMHz, double predelaySamples, double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(sinogram, "sinogram");
    checkSubpointGeometry(subpointPositions, weights);
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == subpointPositions.size(2),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == subpointPositions.device(),
                "sinogram and subpoint positions must share a CUDA device");

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty({nz, ny, nx}, sinogram.options());
    const auto grid = makeGrid(output, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const int numSubpoints = static_cast<int>(subpointPositions.size(1));
    const int numSensors = static_cast<int>(subpointPositions.size(2));
    const size_t numVoxels = static_cast<size_t>(output.numel());
    constexpr unsigned int threads = 256;
    const unsigned int blocks = static_cast<unsigned int>(
        (numVoxels + threads - 1) / threads);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    diskAdjointPrecomputedKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), subpointPositions.data_ptr<float>(),
        weights.data_ptr<float>(), output.data_ptr<float>(),
        numVoxels, numSensors, numSubpoints, grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor sparse_disk_forward(
    torch::Tensor sourcePositions, torch::Tensor sourceAmplitudes,
    torch::Tensor sensors, torch::Tensor offsets, torch::Tensor weights,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double soundSpeedMps)
{
    checkSparseSources(sourcePositions, sourceAmplitudes);
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(sourcePositions.device() == sensors.device(),
                "sources and geometry must share a CUDA device");
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, soundSpeedMps);
    const size_t numSources = static_cast<size_t>(sourceAmplitudes.numel());
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));

    c10::cuda::CUDAGuard guard(sourceAmplitudes.device());
    auto output = torch::zeros(
        {numSamples, static_cast<int64_t>(numSensors)},
        sourceAmplitudes.options());
    if (numSources == 0) return output;
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numSources + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sourceAmplitudes.get_device()).stream();
    sparseDiskForwardKernel<<<blocks, threads, 0, stream>>>(
        sourcePositions.data_ptr<float>(), sourceAmplitudes.data_ptr<float>(),
        sensors.data_ptr<float>(), offsets.data_ptr<float>(),
        weights.data_ptr<float>(), output.data_ptr<float>(),
        numSources, numSensors, numSubpoints, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor sparse_disk_adjoint(
    torch::Tensor sinogram, torch::Tensor sourcePositions,
    torch::Tensor sensors, torch::Tensor offsets, torch::Tensor weights,
    double fsMHz, double predelaySamples, double soundSpeedMps)
{
    checkTensor(sinogram, "sinogram");
    checkTensor(sourcePositions, "source_positions");
    checkGeometry(sensors, offsets, weights);
    TORCH_CHECK(sourcePositions.dim() == 2 && sourcePositions.size(0) == 3,
                "source_positions must have shape [3,K]");
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device() &&
                sourcePositions.device() == sensors.device(),
                "sinogram, sources, and geometry must share a CUDA device");
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const size_t numSources = static_cast<size_t>(sourcePositions.size(1));
    const int numSensors = static_cast<int>(sensors.size(1));
    const int numSubpoints = static_cast<int>(offsets.size(1));

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty(
        {static_cast<int64_t>(numSources)}, sinogram.options());
    if (numSources == 0) return output;
    constexpr unsigned int threads = 256;
    const unsigned int blocks = static_cast<unsigned int>(
        (numSources + threads - 1) / threads);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    sparseDiskAdjointKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sourcePositions.data_ptr<float>(),
        sensors.data_ptr<float>(), offsets.data_ptr<float>(),
        weights.data_ptr<float>(), output.data_ptr<float>(),
        numSources, numSensors, numSubpoints, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor analytic_disk_forward(
    torch::Tensor volume, torch::Tensor sensors, double radiusMm,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(volume, "volume");
    checkSensors(sensors);
    TORCH_CHECK(volume.device() == sensors.device(),
                "volume and sensors must share a CUDA device");
    TORCH_CHECK(radiusMm > 0.0, "receiver radius must be positive");
    const auto grid = makeGrid(volume, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, soundSpeedMps);
    const size_t numVoxels = static_cast<size_t>(volume.numel());
    const int numSensors = static_cast<int>(sensors.size(1));

    c10::cuda::CUDAGuard guard(volume.device());
    auto output = torch::zeros({numSamples, numSensors}, volume.options());
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numVoxels + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        volume.get_device()).stream();
    analyticDiskForwardKernel<<<blocks, threads, 0, stream>>>(
        volume.data_ptr<float>(), sensors.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors,
        static_cast<float>(radiusMm), grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor analytic_disk_adjoint(
    torch::Tensor sinogram, torch::Tensor sensors, double radiusMm,
    int64_t nx, int64_t ny, int64_t nz,
    double fsMHz, double predelaySamples, double soundSpeedMps,
    double x0, double y0, double z0,
    double dx, double dy, double dz)
{
    checkTensor(sinogram, "sinogram");
    checkSensors(sensors);
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device(),
                "sinogram and sensors must share a CUDA device");
    TORCH_CHECK(radiusMm > 0.0, "receiver radius must be positive");

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty({nz, ny, nx}, sinogram.options());
    const auto grid = makeGrid(output, x0, y0, z0, dx, dy, dz);
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const size_t numVoxels = static_cast<size_t>(output.numel());
    const int numSensors = static_cast<int>(sensors.size(1));
    constexpr unsigned int threads = 256;
    constexpr unsigned int warpsPerBlock = threads / 32;
    const unsigned int blocks = static_cast<unsigned int>(
        (numVoxels + warpsPerBlock - 1) / warpsPerBlock);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    analyticDiskAdjointWarpKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sensors.data_ptr<float>(),
        output.data_ptr<float>(), numVoxels, numSensors,
        static_cast<float>(radiusMm), grid, acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor analytic_sparse_disk_forward(
    torch::Tensor sourcePositions, torch::Tensor sourceAmplitudes,
    torch::Tensor sensors, double radiusMm,
    int64_t numSamples, double fsMHz, double predelaySamples,
    double soundSpeedMps)
{
    checkSparseSources(sourcePositions, sourceAmplitudes);
    checkSensors(sensors);
    TORCH_CHECK(sourcePositions.device() == sensors.device(),
                "sources and sensors must share a CUDA device");
    TORCH_CHECK(radiusMm > 0.0, "receiver radius must be positive");
    const auto acoustic = makeAcoustic(
        numSamples, fsMHz, predelaySamples, soundSpeedMps);
    const size_t numSources = static_cast<size_t>(sourceAmplitudes.numel());
    const int numSensors = static_cast<int>(sensors.size(1));

    c10::cuda::CUDAGuard guard(sourceAmplitudes.device());
    auto output = torch::zeros(
        {numSamples, static_cast<int64_t>(numSensors)},
        sourceAmplitudes.options());
    if (numSources == 0) return output;
    const dim3 threads(32, 4, 1);
    const dim3 blocks(
        static_cast<unsigned int>((numSources + threads.x - 1) / threads.x),
        static_cast<unsigned int>((numSensors + threads.y - 1) / threads.y),
        1);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sourceAmplitudes.get_device()).stream();
    analyticSparseDiskForwardKernel<<<blocks, threads, 0, stream>>>(
        sourcePositions.data_ptr<float>(), sourceAmplitudes.data_ptr<float>(),
        sensors.data_ptr<float>(), output.data_ptr<float>(),
        numSources, numSensors, static_cast<float>(radiusMm), acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

torch::Tensor analytic_sparse_disk_adjoint(
    torch::Tensor sinogram, torch::Tensor sourcePositions,
    torch::Tensor sensors, double radiusMm,
    double fsMHz, double predelaySamples, double soundSpeedMps)
{
    checkTensor(sinogram, "sinogram");
    checkTensor(sourcePositions, "source_positions");
    checkSensors(sensors);
    TORCH_CHECK(sourcePositions.dim() == 2 && sourcePositions.size(0) == 3,
                "source_positions must have shape [3,K]");
    TORCH_CHECK(sinogram.dim() == 2 &&
                sinogram.size(1) == sensors.size(1),
                "sinogram must have shape [numSamples,N]");
    TORCH_CHECK(sinogram.device() == sensors.device() &&
                sourcePositions.device() == sensors.device(),
                "sinogram, sources, and sensors must share a CUDA device");
    TORCH_CHECK(radiusMm > 0.0, "receiver radius must be positive");
    const auto acoustic = makeAcoustic(
        sinogram.size(0), fsMHz, predelaySamples, soundSpeedMps);
    const size_t numSources = static_cast<size_t>(sourcePositions.size(1));
    const int numSensors = static_cast<int>(sensors.size(1));

    c10::cuda::CUDAGuard guard(sinogram.device());
    auto output = torch::empty(
        {static_cast<int64_t>(numSources)}, sinogram.options());
    if (numSources == 0) return output;
    constexpr unsigned int threads = 256;
    const unsigned int blocks = static_cast<unsigned int>(
        (numSources + threads - 1) / threads);
    const cudaStream_t stream = at::cuda::getCurrentCUDAStream(
        sinogram.get_device()).stream();
    analyticSparseDiskAdjointKernel<<<blocks, threads, 0, stream>>>(
        sinogram.data_ptr<float>(), sourcePositions.data_ptr<float>(),
        sensors.data_ptr<float>(), output.data_ptr<float>(),
        numSources, numSensors, static_cast<float>(radiusMm), acoustic);
    C10_CUDA_KERNEL_LAUNCH_CHECK();
    return output;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("forward", &disk_forward,
          "Exact disk-SIR48 forward projector (CUDA)");
    m.def("adjoint", &disk_adjoint,
          "Exact disk-SIR48 adjoint projector (CUDA)");
    m.def("adjoint_warp", &disk_adjoint_warp,
          "Exact disk-SIR48 warp-parallel adjoint projector (CUDA)");
    m.def("dual_speed_forward", &dual_speed_disk_forward,
          "Planar dual-speed disk-SIR quadrature forward projector (CUDA)");
    m.def("dual_speed_adjoint", &dual_speed_disk_adjoint,
          "Matched planar dual-speed disk-SIR quadrature adjoint (CUDA)");
    m.def("forward_precomputed", &disk_forward_precomputed,
          "Exact disk-SIR forward with absolute sub-receiver coordinates (CUDA)");
    m.def("adjoint_precomputed", &disk_adjoint_precomputed,
          "Exact disk-SIR adjoint with absolute sub-receiver coordinates (CUDA)");
    m.def("sparse_forward", &sparse_disk_forward,
          "Exact disk-SIR sparse-source forward projector (CUDA)");
    m.def("sparse_adjoint", &sparse_disk_adjoint,
          "Exact disk-SIR sparse-source amplitude adjoint (CUDA)");
    m.def("analytic_forward", &analytic_disk_forward,
          "Continuous circular-receiver SIR forward projector (CUDA)");
    m.def("analytic_adjoint", &analytic_disk_adjoint,
          "Matched continuous circular-receiver SIR adjoint (CUDA)");
    m.def("analytic_sparse_forward", &analytic_sparse_disk_forward,
          "Continuous circular-receiver sparse forward projector (CUDA)");
    m.def("analytic_sparse_adjoint", &analytic_sparse_disk_adjoint,
          "Continuous circular-receiver sparse amplitude adjoint (CUDA)");
}
