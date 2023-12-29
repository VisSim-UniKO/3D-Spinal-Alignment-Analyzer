from typing import List, Tuple
from sys import exit

import argparse

from vtk import (
    vtkActor,
    vtkCellPicker,
    vtkNamedColors,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
)
from vtkmodules.util.misc import calldata_type
from vtkmodules.vtkCommonCore import VTK_OBJECT

from software_flow import (
    IdSet,
    Selection,
    add,
    find_candidates,
    xing2017,
)
from vtk_convenience import (
    find_closest_point_id,
    PickedPoint,
    PointPickerInteractorStyle,
    load_stl,
)

# harmless globals
Colors = vtkNamedColors()

def setup(renderer: vtkRenderer, vertebra_actors: List[vtkActor]) -> Tuple[vtkRenderWindow, vtkRenderWindowInteractor]:
    """
    Prepare a vtk application window with all vtkActors from
    'vertebra_actors' as clickable objects.

    Positional argument:
    renderer - main vtkRenderer that contains all vertebra elements
    vertebra_actors - all clickable actors, that are assigned vtkPolyDataMappers
    representing a vertebra
    """
    renderer.SetBackground(Colors.GetColor3d("BurlyWood"))

    render_window = vtkRenderWindow()
    render_window.SetSize(900, 300)
    render_window.SetWindowName("Xing2017 - Cobb Measurement")
    render_window.AddRenderer(renderer)

    point_picker = vtkCellPicker()
    point_picker.PickFromListOn()
    for actor in vertebra_actors:
        point_picker.AddPickList(actor)

    style = PointPickerInteractorStyle()
    style.AddObserver(
        PointPickerInteractorStyle.PointPickEvent,
        point_select_callback,
    )

    interactor = vtkRenderWindowInteractor()
    interactor.SetPicker(point_picker)
    interactor.SetRenderWindow(render_window)
    interactor.SetInteractorStyle(style)
    
    return render_window, interactor

@calldata_type(VTK_OBJECT)
def point_select_callback(obj, event, point: PickedPoint):
    """
    Callback to be executed when clicked on a vertebra.
    When executed twice, a cobb angle calculation is triggered.
    For that calculation it is assumed, that first a point on
    the top endplate was performed, then on bottom endplate.
    """
    if not hasattr(point_select_callback, "selections"):
        point_select_callback.selections = []

    candidate_ids: IdSet
    candidates: vtkUnstructuredGrid
    candidate_ids, candidates = find_candidates(point.dataset)
    nearest_candidate: int = find_closest_point_id(
        candidates,
        position=point.coordinate,
    )
    candidate: int = find_closest_point_id(
        point.dataset,
        position=candidates.GetPoint(nearest_candidate),
    )

    selection = Selection(point.dataset, candidate, candidate_ids)
    point_select_callback.selections.append(selection)
    if len(point_select_callback.selections) == 2:
        print(xing2017(*point_select_callback.selections))
        exit()

def median_angle(*vertebra_paths: List[str], epsilon: float) -> None:
    vertebrae = [load_stl(p) for p in vertebra_paths]
    candidate_lists = [find_candidates(v, epsilon=epsilon, restricted=True)[0] for v in vertebrae]

    for first_id in candidate_lists[0]:
        for second_id in candidate_lists[1]:
            first_point = Selection(vertebrae[0], first_id, candidate_lists[0])
            second_point = Selection(vertebrae[1], second_id, candidate_lists[1])
            print(xing2017(first_point, second_point))
    exit()

def angle_between(*vertebra_paths: List[str], epsilon: float) -> None:
    " Putting together all pieces. "
    renderer = vtkRenderer()
    vertebra_actors: List[vtkActor] = [
        add(
            actor,
            renderer=renderer,
            point_extractor_func=lambda v: find_candidates(v, epsilon=epsilon),
        )
        for actor in vertebra_paths
    ]

    window, interactor = setup(renderer, vertebra_actors=vertebra_actors)
    window.Render()
    interactor.Start()

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="Xin2017",
        description="Alternative method to calculate the Cobb angle",
    )
    parser.add_argument("top_vertebra", metavar="PATH", type=str, help="Path to STL file.")
    parser.add_argument("bottom_vertebra", metavar="PATH", type=str, help="Path to STL file.")
    parser.add_argument("-t", "--threshold", metavar="LIM", type=float, default=0.01, help="Control the sensitivity for POI detection (default: 0.01)")
    parser.add_argument("--all", action="store_true", help="Do not select a specific POI pair, but calculate all pairs.")
    args = parser.parse_args()
    if args.all:
        median_angle(args.top_vertebra, args.bottom_vertebra, epsilon=args.threshold)
    else:
        angle_between(args.top_vertebra, args.bottom_vertebra, epsilon=args.threshold)

