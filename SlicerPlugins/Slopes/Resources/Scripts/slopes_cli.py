from argparse import ArgumentParser, FileType

from numpy import array

from morphology import Spine
from vtk_convenience import load_stl

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

    Arguments = Parser.parse_args()
    Vertebrae = [load_stl(file) for file in Arguments.filenames]
    SpineRepr = Spine(
        Vertebrae,
        lateral_axis=array(Arguments.right),
        slice_thickness=Arguments.thickness,
        max_angle=Arguments.max_angle,
    )
    print(*SpineRepr.angles, sep=", ")
