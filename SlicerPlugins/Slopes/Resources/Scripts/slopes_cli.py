from argparse import ArgumentParser, FileType
from json import dumps
from sys import exit

from numpy import array, inf, ndarray, set_printoptions

from morphology import Spine
from vtk_convenience import load_stl

def extract_axis(spine: Spine, index: int) -> ndarray:
    vertebra = spine[index]
    orientation = vertebra.orientation
    return array([orientation.left, orientation.back, orientation.up])

def extract_axes(spine: Spine) -> ndarray:
    return array([
        extract_axis(spine, i)
        for i, _ in enumerate(spine)
    ])

if __name__ == '__main__':
    Parser = ArgumentParser(
        prog='Slopes',
        description='Calculate the superior endplate angles for a given set of vertebra STL files.',
    )
    Parser.add_argument(
        'filenames',
        metavar='FILES',
        type=str,
        nargs='+',
        help='Path to STL files, each containing a single vertebra. Minimum number of files is two.',
    )
    Parser.add_argument(
        '-r',
        '--right',
        metavar='FLOAT',
        type=float,
        nargs=3,
        default=[1.0,0.0,0.0],
        help='Direction of that axis, where a subjects right shoulder would point towards. (default: 1 0 0)',
    )
    Parser.add_argument(
        '--thickness',
        metavar='THICK',
        type=float,
        default=0.25,
        help="Thickness of the centroid excerpt to consider. Given in ratio to the vertebra's absolute width (default: 0.25)",
    )
    Parser.add_argument(
        '--max-angle',
        metavar='ANGLE',
        type=float,
        default=45.0,
        help="Maximum angle a face's normal can diverge from the general up direction to be considered part of the superior endplate. (default: 45)",
    )
    Parser.add_argument(
        '-p',
        '--output-local-axes',
        action='store_true',
        help='Print all set of local axes for each individual vertebra',
    )
    Parser.add_argument(
        '-o',
        '--output-axis',
        metavar='INDEX',
        type=int,
        help='Output a specific local set of local axes. The target vertebra is indicated by the zero-based value, passed by INDEX.',
    )

    Arguments = Parser.parse_args()
    Vertebrae = [load_stl(file) for file in Arguments.filenames]
    SpineRepr = Spine(
        Vertebrae,
        lateral_axis=array(Arguments.right),
        slice_thickness=Arguments.thickness,
        max_angle=Arguments.max_angle,
    )
    if not Arguments.output_axis is None:
        print(dumps(extract_axis(SpineRepr, Arguments.output_axis).tolist()))
        exit()
    if Arguments.output_local_axes:
        set_printoptions(threshold=inf)
        print(dumps(extract_axes(SpineRepr).tolist()))
        exit()

    print(*SpineRepr.angles, sep=", ")

