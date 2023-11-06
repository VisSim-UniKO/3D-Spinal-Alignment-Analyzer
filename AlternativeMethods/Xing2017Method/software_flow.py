from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from math import acos, degrees
from typing import List, Set, Tuple

from numpy import (
    apply_along_axis,
    argwhere,
    array,
    mean,
    ndarray,
    vstack,
)
from numpy.linalg import norm, svd
from vtk import (
    vtkActor,
    vtkDataSetMapper,
    vtkIdList,
    vtkNamedColors,
    vtkPointSet,
    vtkPolyDataNormals,
)

from vtk_convenience import (
    add,
    calc_gaussian_curvature,
    calc_mean_curvature,
    colorize,
    Colors,
    extract_points_by_ids,
    IdSet,
    load_stl,
)

@dataclass
class Selection:
    vertebra: vtkDataSet
    click_id: int
    candidates: IdSet

class SurfaceType(IntEnum):
    Ridge = 2
    SaddleRidge = 3
    None_ = 4
    Flat = 5
    MinimalSurface = 6


# Xing2017 specific funtionality
def tolerance_sign(H: float, K: float, epsilon: float):
    """
    Tolerance sign function balances contributions of mean curvature and
    Gaussian curvature.

    Arguments:
    H - Mean curvature of edges around a vertex
    K - Gaussian curvature of a vertex
    epsilon - control parameter for the final surface type
    """
    return 1.0 + 3.0 * ( 1.0 + sign(H, epsilon) ) + ( 1.0 - sign(K, epsilon))

def sign(x: float, epsilon: float) -> int:
    """
    Sign funtion with interval [-epsilon;epsilon] returning 0.
    """
    if x > epsilon:
        return 1
    elif x < -epsilon:
        return -1
    else:
        return 0

def find_candidates(
    vertebra: vtkPolyData,
    surface_type: SurfaceType=SurfaceType.Flat,
    epsilon: float=0.01
) -> Tuple[Set[int], vtkPointSet]:
    """
    Return candidate points from 'vertebra'.
    Candidates are points that have a 'surface_type' type surrounding surface.

    Result consist of first:
        - the IDs of candidates in geometry 'vertebra'
        - a vtkPointSet only consisting of candidate points
    """
    candidate_ids = find_candidate_ids(
        calc_mean_curvature(vertebra),
        calc_gaussian_curvature(vertebra),
        surface_type=surface_type,
        epsilon=epsilon
    )

    return set(candidate_ids), extract_points_by_ids(vertebra, ids=candidate_ids)

def find_candidate_ids(H: VTKArray, K: VTKArray, surface_type: SurfaceType, epsilon: float) -> ndarray:
    """
    Return IDs in 'H' and 'K' that qualify as candidates.

    Positional arguments:
    H - Mean curvatures of edges around vertices
    K - Gaussian curvatures of vertices
    surface_type - shape of surrounding surface for any given vertex
    epsilon - tolarance for shape identification
    """
    curvatures = vstack((H, K,))
    classification = apply_along_axis(lambda row: tolerance_sign(*row, epsilon=epsilon), 0, curvatures)
    return argwhere(classification==surface_type).flatten()

def get_adjacent_points(vertebra: vtkPolyData, id_: int) -> ndarray:
    """
    Return a numpy array of point coordinates of neighbors around vertex
    with ID 'id_' from 'vertebra'.
    """
    def cell_points(cell_id: int):
        points = vtkIdList()
        vertebra.GetCellPoints(cell_id, points)
        return [points.GetId(i) for i in range(points.GetNumberOfIds())]

    cells = vtkIdList()
    vertebra.GetPointCells(id_, cells)

    points = []
    for cell in range(cells.GetNumberOfIds()):
        points += cell_points(cells.GetId(cell))
    return points

def candidate_filter(seed_normal: ndarray, candidate_normal: ndarray, threshold: float) -> bool:
    """
    Return false if euklidean distance between 'seed_normal' and 'candidate_normal' is
    greater than threshold. Else true.
    """
    return norm(candidate_normal - seed_normal) < threshold


def grow_region(vertebra: vtkPolyData, seed_id: int) -> Set:
    """
    Grow a surface area along 'vertebra' from point with ID 'seed_id'.
    New vertices should have a similar normal to point 'seed_id'.
    """
    vertebra.BuildLinks()
    normal_filter = vtkPolyDataNormals()
    normal_filter.ComputePointNormalsOn()
    normal_filter.ComputeCellNormalsOff()
    normal_filter.SetInputData(vertebra)
    normal_filter.Update()
    normals = normal_filter.GetOutput().GetPointData().GetNormals()

    number_of_points = vertebra.GetNumberOfPoints()
    visited_points = set()
    candidates = [seed_id]
    plane_points = {seed_id}

    while candidates:
        candidate = candidates.pop()
        neighbors = get_adjacent_points(vertebra, id_=candidate)
        visited_points.add(candidate)

        for neighbor in neighbors:
            if neighbor in visited_points != -1:
                continue
            if candidate_filter(
                array(normals.GetTuple(seed_id)),
                array(normals.GetTuple(neighbor)),
                threshold=0.5,
            ):
                candidates.append(neighbor)
                plane_points.add(neighbor)

    return plane_points

def xing2017(superior_selection: Selection, inferior_selection: Selection) -> float:
    """
    Return theta_S as the sagittal angle between endplates from '*_selection's.
    """
    superior_vector: ndarray = detect_orientation(superior_selection)
    inferior_vector: ndarray = detect_orientation(inferior_selection)
    theta_sagittal = degrees(acos(
        inferior_vector.dot(superior_vector) \
        / (norm(superior_vector) * norm(inferior_vector))
    ))

    return 180.0 - theta_sagittal

def detect_orientation(selection: Selection) -> ndarray:
    """
    From a user specific point selection 'selection', grow
    a region with similar surface structure.
    All candidates - as defined in Xing2017 - that are not
    part of this region are rejected. From the remainders
    construct a plane and it's normal in a sagittal projection.

    Return the sagittal orientation as a 3d vector.
    """
    plane_points: IdSet = grow_region(selection.vertebra, seed_id=selection.click_id)
    points_of_interest = array([
        selection.vertebra.GetPoint(id_)
        for id_ in plane_points & selection.candidates
    ])
    
    center = mean(points_of_interest, axis=0)
    points_of_interest -= center
    normal = svd(points_of_interest)[-1][2]

    projection_matrix = array([
        [1,1,0,],
        [1,0,1,],
        [0,1,1,],
    ])
    sagittal_vector = (normal * projection_matrix)[2]
    return sagittal_vector
