import pytest
from astropy import units as u
from astropy.coordinates import Angle, ICRS, SkyCoord
from astropy.tests.helper import assert_quantity_allclose
from glue.core.roi import CircularROI, EllipticalROI, RectangularROI
from numpy.testing import assert_allclose
from photutils.aperture import (CircularAperture, SkyCircularAperture,
                                EllipticalAperture, SkyEllipticalAperture,
                                RectangularAperture, SkyRectangularAperture,
                                CircularAnnulus, SkyCircularAnnulus,
                                EllipticalAnnulus, SkyEllipticalAnnulus,
                                RectangularAnnulus, SkyRectangularAnnulus)
from regions import (CirclePixelRegion, CircleSkyRegion,
                     EllipsePixelRegion, EllipseSkyRegion,
                     RectanglePixelRegion, CircleAnnulusPixelRegion,
                     EllipseAnnulusPixelRegion, RectangleAnnulusPixelRegion,
                     PolygonPixelRegion, PolygonSkyRegion,
                     PixCoord)

from jdaviz.core.region_translators import (
    _create_polygon_skyregion_from_coords, _create_circle_skyregion_from_coords,
    _create_ellipse_skyregion_from_coords, is_stcs_string, stcs_string2region,
    regions2roi, regions2aperture, aperture2regions)


# TODO: Use proper method from upstream when that is available.
def compare_region_shapes(reg1, reg2):
    assert reg1.__class__ == reg2.__class__
    for param in reg1._params:
        par1 = getattr(reg1, param)
        par2 = getattr(reg2, param)
        if isinstance(par1, PixCoord):
            assert_allclose(par1.xy, par2.xy)
        elif isinstance(par1, SkyCoord):
            assert par1 == par2
        elif isinstance(par1, u.Quantity):
            assert_quantity_allclose(par1, par2)
        else:
            assert_allclose(par1, par2)


def test_translation_circle(image_2d_wcs):
    region_shape = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, CircularAperture)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.r, region_shape.radius)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyCircularAperture)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.r, region_sky.radius)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    with pytest.raises(ValueError, match='regions shape only accepts scalar x and y positions'):
        aperture2regions(CircularAperture(((10, 20), (30, 40)), 3))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        CirclePixelRegion(center=PixCoord(x=[0, 42], y=[1, 43]), radius=4.2)
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        CirclePixelRegion(center=PixCoord(x=42, y=43), radius=[1, 4.2])


def test_translation_circle_roi(image_2d_wcs):
    region_shape = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    roi_pix = regions2roi(region_shape)
    assert isinstance(roi_pix, CircularROI)
    assert_allclose((roi_pix.xc, roi_pix.yc, roi_pix.radius), (42, 43, 4.2))

    region_sky = region_shape.to_sky(image_2d_wcs)
    roi_sky = regions2roi(region_sky, wcs=image_2d_wcs)
    assert isinstance(roi_sky, CircularROI)
    assert_allclose((roi_sky.xc, roi_sky.yc, roi_sky.radius),
                    (roi_pix.xc, roi_pix.yc, roi_pix.radius))

    with pytest.raises(ValueError, match='WCS must be provided'):
        regions2roi(region_sky)


def test_translation_ellipse(image_2d_wcs):
    region_shape = EllipsePixelRegion(
        center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle(30, 'deg'))
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, EllipticalAperture)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.a * 2, region_shape.width)
    assert_allclose(aperture.b * 2, region_shape.height)
    assert_quantity_allclose(aperture.theta, region_shape.angle)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyEllipticalAperture)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.a * 2, region_sky.width)
    assert_quantity_allclose(aperture_sky.b * 2, region_sky.height)
    assert_quantity_allclose(aperture_sky.theta + (90 * u.deg), region_sky.angle)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        EllipsePixelRegion(
            center=PixCoord(x=[0, 42], y=[1, 43]), width=16, height=10, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipsePixelRegion(
            center=PixCoord(x=42, y=43), width=[1, 16], height=10, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipsePixelRegion(
            center=PixCoord(x=42, y=43), width=16, height=[1, 10], angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipsePixelRegion(
            center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle([0, 30], 'deg'))


def test_translation_ellipse_roi(image_2d_wcs):
    region_shape = EllipsePixelRegion(
        center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle(30, 'deg'))
    roi_pix = regions2roi(region_shape)
    assert isinstance(roi_pix, EllipticalROI)
    assert_allclose((roi_pix.xc, roi_pix.yc, roi_pix.radius_x, roi_pix.radius_y, roi_pix.theta),
                    (42, 43, 8.0, 5.0, 0.5235987755982988))

    region_sky = region_shape.to_sky(image_2d_wcs)
    roi_sky = regions2roi(region_sky, wcs=image_2d_wcs)
    assert isinstance(roi_sky, EllipticalROI)
    assert_allclose((roi_sky.xc, roi_sky.yc, roi_sky.radius_x, roi_sky.radius_y, roi_sky.theta),
                    (roi_pix.xc, roi_pix.yc, roi_pix.radius_x, roi_pix.radius_y, roi_pix.theta))


def test_translation_rectangle(image_2d_wcs):
    region_shape = RectanglePixelRegion(
        center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle(30, 'deg'))
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, RectangularAperture)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.w, region_shape.width)
    assert_allclose(aperture.h, region_shape.height)
    assert_quantity_allclose(aperture.theta, region_shape.angle)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyRectangularAperture)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.w, region_sky.width)
    assert_quantity_allclose(aperture_sky.h, region_sky.height)
    assert_quantity_allclose(aperture_sky.theta + (90 * u.deg), region_sky.angle)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        RectanglePixelRegion(
            center=PixCoord(x=[0, 42], y=[1, 43]), width=16, height=10, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectanglePixelRegion(
            center=PixCoord(x=42, y=43), width=[1, 16], height=10, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectanglePixelRegion(
            center=PixCoord(x=42, y=43), width=16, height=[1, 10], angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectanglePixelRegion(
            center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle([0, 30], 'deg'))


def test_translation_rectangle_roi(image_2d_wcs):
    region_shape = RectanglePixelRegion(
        center=PixCoord(x=42, y=43), width=16, height=10, angle=Angle(30, 'deg'))
    roi_pix = regions2roi(region_shape)
    assert isinstance(roi_pix, RectangularROI)
    assert_allclose((roi_pix.xmin, roi_pix.xmax, roi_pix.ymin, roi_pix.ymax, roi_pix.theta),
                    (34, 50, 38, 48, 0.5235987755982988))

    region_sky = region_shape.to_sky(image_2d_wcs)
    roi_sky = regions2roi(region_sky, wcs=image_2d_wcs)
    assert isinstance(roi_sky, RectangularROI)
    assert_allclose((roi_sky.xmin, roi_sky.xmax, roi_sky.ymin, roi_sky.ymax, roi_sky.theta),
                    (roi_pix.xmin, roi_pix.xmax, roi_pix.ymin, roi_pix.ymax, roi_pix.theta))


def test_translation_circle_annulus(image_2d_wcs):
    region_shape = CircleAnnulusPixelRegion(
        center=PixCoord(x=42, y=43), inner_radius=5, outer_radius=8)
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, CircularAnnulus)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.r_in, region_shape.inner_radius)
    assert_allclose(aperture.r_out, region_shape.outer_radius)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyCircularAnnulus)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.r_in, region_sky.inner_radius)
    assert_quantity_allclose(aperture_sky.r_out, region_sky.outer_radius)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        CircleAnnulusPixelRegion(
            center=PixCoord(x=[0, 42], y=[1, 43]), inner_radius=5, outer_radius=8)
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        CircleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_radius=[1, 5], outer_radius=8)
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        CircleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_radius=5, outer_radius=[8, 10])


def test_translation_ellipse_annulus(image_2d_wcs):
    region_shape = EllipseAnnulusPixelRegion(
        center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
        outer_height=6.5, angle=Angle(30, 'deg'))
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, EllipticalAnnulus)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.a_in * 2, region_shape.inner_width)
    assert_allclose(aperture.a_out * 2, region_shape.outer_width)
    assert_allclose(aperture.b_in * 2, region_shape.inner_height)
    assert_allclose(aperture.b_out * 2, region_shape.outer_height)
    assert_quantity_allclose(aperture.theta, region_shape.angle)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyEllipticalAnnulus)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.a_in * 2, region_sky.inner_width)
    assert_quantity_allclose(aperture_sky.a_out * 2, region_sky.outer_width)
    assert_quantity_allclose(aperture_sky.b_in * 2, region_sky.inner_height)
    assert_quantity_allclose(aperture_sky.b_out * 2, region_sky.outer_height)
    assert_quantity_allclose(aperture_sky.theta + (90 * u.deg), region_sky.angle)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=[0, 42], y=[1, 43]), inner_width=5.5, inner_height=3.5,
            outer_width=8.5, outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=[1, 5.5], inner_height=3.5, outer_width=8.5,
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=[1, 3.5], outer_width=8.5,
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=[8.5, 10],
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
            outer_height=[6.5, 10], angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        EllipseAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
            outer_height=6.5, angle=Angle([0, 30], 'deg'))


def test_translation_rectangle_annulus(image_2d_wcs):
    region_shape = RectangleAnnulusPixelRegion(
        center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
        outer_height=6.5, angle=Angle(30, 'deg'))
    aperture = regions2aperture(region_shape)
    assert isinstance(aperture, RectangularAnnulus)
    assert_allclose(aperture.positions, region_shape.center.xy)
    assert_allclose(aperture.w_in, region_shape.inner_width)
    assert_allclose(aperture.w_out, region_shape.outer_width)
    assert_allclose(aperture.h_in, region_shape.inner_height)
    assert_allclose(aperture.h_out, region_shape.outer_height)
    assert_quantity_allclose(aperture.theta, region_shape.angle)

    region_sky = region_shape.to_sky(image_2d_wcs)
    aperture_sky = regions2aperture(region_sky)
    assert isinstance(aperture_sky, SkyRectangularAnnulus)
    assert aperture_sky.positions == region_sky.center  # SkyCoord
    assert_quantity_allclose(aperture_sky.w_in, region_sky.inner_width)
    assert_quantity_allclose(aperture_sky.w_out, region_sky.outer_width)
    assert_quantity_allclose(aperture_sky.h_in, region_sky.inner_height)
    assert_quantity_allclose(aperture_sky.h_out, region_sky.outer_height)
    assert_quantity_allclose(aperture_sky.theta + (90 * u.deg), region_sky.angle)

    # Roundtrip
    compare_region_shapes(region_shape, aperture2regions(aperture))
    compare_region_shapes(region_sky, aperture2regions(aperture_sky))

    # NOTE: If these no longer fail, we also have to account for non-scalar inputs.
    # Assume this is representative for the sky counterpart too.
    with pytest.raises(ValueError, match='must be a scalar PixCoord'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=[0, 42], y=[1, 43]), inner_width=5.5, inner_height=3.5,
            outer_width=8.5, outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=[1, 5.5], inner_height=3.5, outer_width=8.5,
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=[1, 3.5], outer_width=8.5,
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=[8.5, 10],
            outer_height=6.5, angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
            outer_height=[6.5, 10], angle=Angle(30, 'deg'))
    with pytest.raises(ValueError, match=r'must be .* scalar'):
        RectangleAnnulusPixelRegion(
            center=PixCoord(x=42, y=43), inner_width=5.5, inner_height=3.5, outer_width=8.5,
            outer_height=6.5, angle=Angle([0, 30], 'deg'))


def test_translation_polygon():
    region_shape = PolygonPixelRegion(vertices=PixCoord(x=[1, 2, 2], y=[1, 1, 2]))
    with pytest.raises(NotImplementedError, match='is not supported'):
        regions2aperture(region_shape)
    with pytest.raises(NotImplementedError, match='is not supported'):
        regions2roi(region_shape)


def test___create_polygon_skyregion_from_coords():
    coords = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    reg = _create_polygon_skyregion_from_coords(coords)
    assert isinstance(reg, PolygonSkyRegion)
    assert_allclose(reg.vertices.ra.degree, [10, 30, 50])
    assert_allclose(reg.vertices.dec.degree, [20, 40, 60])
    # Check that the default frame is ICRS
    assert isinstance(reg.vertices.frame, ICRS)
    # Check that the default unit is deg
    assert reg.vertices.ra.unit == u.deg


def test___create_circle_skyregion_from_coords():
    coords = [10.0, 20.0, 30.0]
    reg = _create_circle_skyregion_from_coords(coords)
    assert isinstance(reg, CircleSkyRegion)
    assert_allclose(reg.center.ra.degree, 10)
    assert_allclose(reg.center.dec.degree, 20)
    # Check that the default frame is ICRS
    assert isinstance(reg.center.frame, ICRS)
    # Check that the default unit is deg
    assert reg.center.ra.unit == u.deg


def test___create_ellipse_skyregion_from_coords():
    coords = [10.0, 20.0, 30.0, 40.0, 50.0]
    reg = _create_ellipse_skyregion_from_coords(coords)
    assert isinstance(reg, EllipseSkyRegion)
    assert_allclose(reg.center.ra.degree, 10)
    assert_allclose(reg.center.dec.degree, 20)
    # Check that the default frame is ICRS
    assert isinstance(reg.center.frame, ICRS)
    # Check that the default unit is deg
    assert reg.center.ra.unit == u.deg


@pytest.mark.parametrize('stcs_string, expected', [
    ('POLYGON ICRS 10.0 20.0', True),
    ('CIRCLE ICRS 10.0 20.0', True),
    ('ELLIPSE ICRS 10.0 20.0', True),
    ('polygon icrs 10.0 20.0', True),
    ('circle icrs 10.0 20.0', True),
    ('ellipse icrs 10.0 20.0', True),
    ('POLYGON J2000 10.0 20.0', True),
    ('CIRCLE J2000 10.0 20.0', True),
    ('ELLIPSE J2000 10.0 20.0', True),
    ('POLYGON FK5 10.0 20.0', True),
    ('CIRCLE FK5 10.0 20.0', True),
    ('ELLIPSE FK5 10.0 20.0', True),
    ('POLYGON 10.0 20.0', True),
    ('CIRCLE 10.0 20.0', True),
    ('ELLIPSE 10.0 20.0', True),
    ('POLYGON ICRS 1.0', False),
    ('POLYGON ICRS 1 2 3', False),
    ('POLYGON 1.0', False),
    ('POLYGON 1 2 3', False),
    ('not a STC-S string', False),
    # Invalid input type (not a string) should return False instead of raising an error
    (123, False),
])
def test_is_stcs_string(stcs_string, expected):
    assert is_stcs_string(stcs_string) is expected


@pytest.mark.parametrize('stcs_string, expected', [
    ('POLYGON ICRS 10.0 20.0 30.0 40.0 50.0 60.0',
     PolygonSkyRegion(vertices=SkyCoord(ra=[10, 30, 50], dec=[20, 40, 60], unit='deg'))),
    ('CIRCLE ICRS 10.0 20.0 30.0',
     CircleSkyRegion(center=SkyCoord(ra=10, dec=20, unit='deg'), radius=30 * u.deg)),
    ('ELLIPSE ICRS 10.0 20.0 30.0 40.0 50.0',
     EllipseSkyRegion(center=SkyCoord(ra=10, dec=20, unit='deg'),
                      width=30 * u.deg, height=40 * u.deg, angle=50 * u.deg)),
])
def test_stcs_string2region_correctness(stcs_string, expected):
    reg = stcs_string2region(stcs_string)
    assert reg == expected


@pytest.mark.parametrize('stcs_string, exception_message', [
    ('CIRCLE ICRS 10', 'Invalid STC-S string'),
    (123, 'STC-S string must be a string.'),
])
def test_stcs_string2region_exceptions(stcs_string, exception_message):
    with pytest.raises(ValueError, match=exception_message):
        stcs_string2region(stcs_string)
