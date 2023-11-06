from enum import Enum
from dataclasses import dataclass
from typing import Callable, Tuple, Set

from numpy import array, ndarray
from vtkmodules.numpy_interface import dataset_adapter
from vtk import (
    vtkAbstractPolyDataReader,
    vtkActor,
    vtkCurvatures,
    vtkDataSet,
    vtkDataSetMapper,
    vtkExtractSelection,
    vtkIdTypeArray,
    vtkInteractorStyleTrackballCamera,
    vtkNamedColors,
    vtkObject,
    vtkPointLocator,
    vtkPointPicker,
    vtkPointSet,
    vtkPolyData,
    vtkPolyDataMapper,
    vtkRemovePolyData,
    vtkRenderer,
    vtkSTLReader,
    vtkSelection,
    vtkSelectionNode,
    vtkUnsignedCharArray,
    vtkUnstructuredGrid,
)

# types
IdSet = Set[int]

# harmless globals
Colors = vtkNamedColors()

class CurvatureType(str, Enum):
    """
    Curvature type identifiers as needed by vtkCurvature.
    """
    Gauss = "Gauss_Curvature"
    Mean = "Mean_Curvature"

@dataclass
class PickedPoint(vtkObject):
    """
    Representation for a point clicked on a vtk geometry.
    """
    id_: int
    dataset: vtkDataSet

    @property
    def coordinate(self) -> Tuple[float, float, float]:
        """
        Return position of a clicked polygon.
        """
        return self.dataset.GetPoint(self.id_)

def convert_array_to_id_type_array(id_array: ndarray) -> vtkIdTypeArray:
    """
    Some vtk filters require vtkIdTypeArrays when processing a list of IDs.
    Return an vtkIdTypeArray from numpy array 'id_array'.
    """
    converted = vtkIdTypeArray()
    for n in range(id_array.size):
        converted.InsertNextValue(id_array[n])
    return converted

def extract_points_by_ids(polydata: vtkPolyData, ids: ndarray) -> vtkPointSet:
    """
    Return a vtkUnstructuredGrid only consisting of points from 'polydata'
    that are to be kept as specified by 'ids'.
    """
    ids = convert_array_to_id_type_array(ids)

    selection_node = vtkSelectionNode()
    selection_node.SetFieldType(vtkSelectionNode.POINT)
    selection_node.SetContentType(vtkSelectionNode.INDICES)
    selection_node.SetSelectionList(ids)

    selection = vtkSelection()
    selection.AddNode(selection_node)

    extractor = vtkExtractSelection()
    extractor.SetInputData(0, polydata)
    extractor.SetInputData(1, selection)
    extractor.Update()

    # Configure output
    selected = vtkUnstructuredGrid()
    selected.ShallowCopy(extractor.GetOutput())
    return selected

def find_closest_point_id(polydata: vtkPointSet, position: Tuple[float, float, float]) -> int:
    """
    Find that point ID in 'polydata', that is closest to global 3d coordinate position.
    """
    point_tree = vtkPointLocator()
    point_tree.SetDataSet(polydata)
    point_tree.BuildLocator()
    return point_tree.FindClosestPoint(position)

class PointPickerInteractorStyle(vtkInteractorStyleTrackballCamera):
    """
    Specialization of a vtkInteractorStyle.
    It constructs a PickedPoint on left mouse button click.
    After, a PointPickEvent is fired.
    """
    PointPickEvent = 1000

    def __init__(self, parent=None) -> None:
        """
        Listen for left mouse button releases.
        """
        self.AddObserver("LeftButtonReleaseEvent", self.OnLeftButtonUp)

    def OnLeftButtonUp(self, obj, event):
        """
        If left mouse button click was performed at an object managed
        by this vtkInteractorStyle's vtkInteractor, notiy all observers
        about the PickedPoint.
        """
        interactor = self.GetInteractor()
        point_picker = interactor.GetPicker()
        point_picker.Pick(
            *interactor.GetEventPosition(),
            0,
            interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
        )
        point = self.get_picked_point(point_picker)
        if point:
            self.InvokeEvent(self.PointPickEvent, point)
        super(vtkInteractorStyleTrackballCamera, self).OnLeftButtonUp()

    @staticmethod
    def get_picked_point(picker: vtkPointPicker) -> PickedPoint:
        """
        Contruckt a PickedPoint.
        """
        picked_point_id = picker.GetPointId()
        if picked_point_id == -1:
            return None

        return PickedPoint(picked_point_id, dataset=picker.GetDataSet())

def colorize(dataset: vtkPointSet, color: Tuple[float, float, float], base_color: Tuple[float, float, float]=None, id_: int=None):
    """
    Change the color of 'dataset'.

    Positional arguments:
    dataset - vtkPointSet to change in color
    color - new color of all (selected) vertices

    Optional arguments:
    base_color - if 'id_' is specified, paint all other vertices in this color
    id_ - chose one point to highlight in color 'color' vs. all others in color
    'base_color'
    """
    colors = vtkUnsignedCharArray()
    colors.SetNumberOfComponents(3)

    for _ in range(dataset.GetNumberOfPoints()):
        colors.InsertNextTuple(color if id_ is None else base_color)

    if not id_ is None:
        colors.SetTuple(id_, color)
        colors.Modified()
        
    dataset.GetPointData().SetScalars(colors)


def calc_gaussian_curvature(polydata: vtkPolyData) -> dataset_adapter.VTKArray:
    """
    Calculate the gaussian curvature to 'polydata's surface.
    """
    return _calc_curvature(polydata, CurvatureType.Gauss)

def calc_mean_curvature(polydata: vtkPolyData) -> dataset_adapter.VTKArray:
    """
    Calculate the mean curvature to 'polydata's surface.
    """
    return _calc_curvature(polydata, CurvatureType.Mean)

def _calc_curvature(polydata: vtkPolyData, curvature_type: CurvatureType) -> dataset_adapter.VTKArray:
    """
    Calculate a curvature to 'polydata's surface.
    Supported curvatures are defined by vtkCurvatures and CurvatureType.
    """
    curvatures = vtkCurvatures()
    curvatures.SetInputData(polydata)

    if curvature_type is CurvatureType.Gauss:
        curvatures.SetCurvatureTypeToGaussian()
    else:
        curvatures.SetCurvatureTypeToMean()
        
    curvatures.Update()
    result = curvatures.GetOutput()
    wrapped_result = dataset_adapter.WrapDataObject(result)
    return wrapped_result.PointData[curvature_type]

def add(
    vertebra_file: str,
    renderer: vtkRenderer,
    point_extractor_func: Callable[[vtkRenderer], Tuple[IdSet, vtkUnstructuredGrid]]
) -> vtkActor:
    """
    Add a vertebra from disc - as defined by 'vertebra_file' - to the view managed by
    'renderer'. The graphic elements consist of a plain geometry and some point from
    'point_extractor_func' layered on top.

    Positional arguments:
    vertebra_file - path to a STL geometry
    renderer - vtkRenderer to add the final geometries to
    point_extractor_func - function to generate a vtkUnstructuredGrid that is to be
    displayed on top of the geometry.
    """
    vertebra: vtkPolyData = load_stl(vertebra_file)
    candidate_ids: IdSet
    candidate_positions: vtkUnstructuredGrid
    candidate_ids, candidate_positions = point_extractor_func(vertebra)
    colorize(candidate_positions, color=Colors.GetColor3ub("Yellow"))
    
    mapper = vtkDataSetMapper()
    mapper.SetInputData(candidate_positions)
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetPointSize(5)
    renderer.AddActor(actor)

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(vertebra)
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(Colors.GetColor3d("MidnightBlue"))
    renderer.AddActor(actor)

    return actor

def _load_geometry(filename: str, reader: vtkAbstractPolyDataReader) -> vtkPolyData:
    """Load the given poly data file, and return a vtkPolyData object for it."""
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

def load_stl(filename: str) -> vtkPolyData:
    """Load the given STL file, and return a vtkPolyData object for it."""
    return _load_geometry(filename, reader=vtkSTLReader())


# Not part of this application. Only some debugging aids.
def invert_id_list(id_list: Set[int], number_of_ids: int) -> ndarray:
    """
    Assuming a continuous list of integer IDs of size 'number_of_ids'.
    Return all IDs that are not in 'id_list'.
    """
    out_set = set(n for n in range(number_of_ids))
    in_set = id_list
    return array(list(out_set - in_set))


def keep_only_ids(polydata: vtkPolyData, ids: ndarray) -> vtkPolyData:
    """
    Remove all IDs from 'polydata' that are not present in 'ids'.
    """
    inverted_ids: ndarray = invert_id_list(ids, number_of_ids=polydata.GetNumberOfPoints())
    inverted_ids: vtkIdTypeArray = convert_array_to_id_type_array(inverted_ids)

    remove_filter = vtkRemovePolyData()
    remove_filter.SetInputData(polydata)
    remove_filter.SetPointIds(inverted_ids)
    remove_filter.Update()
    
    return remove_filter.GetOutput()
