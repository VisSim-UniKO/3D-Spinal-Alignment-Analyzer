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
        point_select_callback.selections.clear()

def main(*vertebra_paths: List[str]) -> None:
    " Putting together all pieces. "
    renderer = vtkRenderer()
    vertebra_actors: List[vtkActor] = [
        add(actor, renderer=renderer, point_extractor_func=find_candidates)
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
    args = parser.parse_args()
    main(args.top_vertebra, args.bottom_vertebra)

