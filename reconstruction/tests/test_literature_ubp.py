"""Analytical checks from pressure functions and the published sphere solution."""
import unittest
import numpy as np
from pa_pipeline.backends.literature_ubp import temporal_term, ubp_points, ubp_volume, UBPProjector


def sphere_data(n=192):
    k=np.arange(n)+.5;z=1-2*k/n;phi=k*np.pi*(3-np.sqrt(5))
    sensors=12*np.column_stack([np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z])
    normals=-sensors/12
    source=np.array([.4,-.2,.6]);radius=.7;speed=1500.
    time=np.arange(1000)/80e6
    distance=np.linalg.norm(sensors-source,axis=1)
    delta=distance[:,None]-speed*1000*time[None]
    # Xu & Wang (2005), section IV: acoustic pressure of a uniform ball.
    pressure=np.where(np.abs(delta)<=radius,delta/(2*distance[:,None]),0).astype('f4')
    return pressure,time,sensors,normals,source,speed


class LiteratureUBPTests(unittest.TestCase):
    def test_constant_and_linear_pressure(self):
        t=np.linspace(-.2,2,30)
        p=np.vstack([np.full(len(t),3.),2+4*t])
        b=temporal_term(p,t)
        np.testing.assert_allclose(b[0],6,atol=1e-6)
        np.testing.assert_allclose(b[1],4,atol=1e-6)

    def test_quadratic_derivative_and_boundary_stencils(self):
        t=np.linspace(0,2,21);b=temporal_term((3+2*t+t*t)[None],t)
        np.testing.assert_allclose(b[0],6-2*t*t,atol=2e-6)

    def test_published_uniform_ball_amplitude(self):
        p,t,s,n,source,c=sphere_data()
        locations=np.vstack([source,source+[.1,.1,0],source+[-.2,0,.1]])
        values=ubp_points(p,t,s,n,locations,sound_speed_m_s=c)
        np.testing.assert_allclose(values,1,atol=.025)

    def test_linear_time_interpolation(self):
        t=np.arange(8,dtype=float)
        engine=UBPProjector(np.zeros((1,8)),t,[[0,0,0]],[[1,0,0]],sound_speed_m_s=.001)
        engine.signal=np.arange(8,dtype='f4')[None]
        actual=engine.evaluate([[2.25,0,0],[7,0,0]])
        np.testing.assert_allclose(actual,[2.25,7])

    def test_solid_angle_and_area_quadrature(self):
        t=np.arange(10,dtype=float)
        result=ubp_points(np.array([[1]*10,[3]*10]),t,[[0,0,0],[0,0,-2]],[[0,0,1],[0,0,1]],
                          [[0,0,2]],sound_speed_m_s=.001,surface_areas=[1,2])
        # Weights: 1/2^2 and 2/4^2; b = 2p.
        np.testing.assert_allclose(result,[(.25*2+.125*6)/.375],rtol=1e-6)

    def test_signed_output(self):
        t=np.arange(10,dtype=float)
        value=ubp_points(-np.ones((1,10)),t,[[0,0,0]],[[1,0,0]],[[2,0,0]],sound_speed_m_s=.001)
        np.testing.assert_array_equal(value,[-2])

    def test_time_truncation_keeps_geometric_denominator(self):
        value=ubp_points(np.ones((2,5)),np.arange(5.),[[0,0,0],[-10,0,0]],[[1,0,0],[1,0,0]],
                         [[2,0,0]],sound_speed_m_s=.001)
        np.testing.assert_allclose(value,[2*(1/4)/(1/4+1/144)],rtol=1e-6)

    def test_normals_are_directed_not_absolute(self):
        value=ubp_points(np.ones((1,5)),np.arange(5.),[[0,0,0]],[[-1,0,0]],[[2,0,0]],sound_speed_m_s=.001)
        np.testing.assert_array_equal(value,[0])

    def test_batching_and_volume_axes(self):
        p,t,s,n,source,c=sphere_data(32);axis=np.linspace(-1,1,5)
        a=ubp_volume(p,t,s,n,[axis,axis,axis],sound_speed_m_s=c,point_batch=17,detector_batch=7)
        k,j,i=np.indices(a.shape);points=np.column_stack([axis[i.ravel()],axis[j.ravel()],axis[k.ravel()]])
        b=ubp_points(p,t,s,n,points,sound_speed_m_s=c,point_batch=50,detector_batch=13)
        np.testing.assert_allclose(a.ravel(),b,atol=2e-6)

    def test_invalid_time_and_complex_rejected(self):
        with self.assertRaises(ValueError):temporal_term(np.ones((2,4)),[0,1,1,2])
        with self.assertRaises(ValueError):temporal_term(np.ones((2,4),dtype=complex),np.arange(4.))

    def test_cpu_cuda_agree(self):
        try:
            import cupy
            if not cupy.cuda.runtime.getDeviceCount():self.skipTest('No CUDA device')
        except ImportError:self.skipTest('No CuPy')
        p,t,s,n,source,c=sphere_data(48);points=np.random.default_rng(10).normal(size=(37,3))
        cpu=ubp_points(p,t,s,n,points,sound_speed_m_s=c,detector_batch=9)
        gpu=ubp_points(p,t,s,n,points,sound_speed_m_s=c,backend='cuda',detector_batch=11)
        np.testing.assert_allclose(cpu,gpu,rtol=2e-6,atol=1e-6)


if __name__=='__main__':unittest.main()
