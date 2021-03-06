import abc

import numpy as np

from . import PointCloud
from .adjacency import (mask_adjacency_array, mask_adjacency_array_tree,
                        reindex_adjacency_array)
from menpo.visualize import PointGraphViewer


class Graph(object):
    r"""
    Abstract class for Graph definitions and manipulation.

    Parameters
    -----------
    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the graph, i.e. an array containing the sets of
        the graph's edges. The numbering of vertices is assumed to start from 0.

        For an undirected graph, the order of an edge's vertices doesn't matter,
        for example:
               |---0---|        adjacency_array = ndarray([[0, 1],
               |       |                                   [0, 2],
               |       |                                   [1, 2],
               1-------2                                   [1, 3],
               |       |                                   [2, 4],
               |       |                                   [3, 4],
               3-------4                                   [3, 5]])
               |
               5

        For a directed graph, we assume that the vertices in the first column of
        the adjacency_array are the fathers and the vertices in the second
        column of the adjacency_array are the children, for example:
               |-->0<--|        adjacency_array = ndarray([[1, 0],
               |       |                                   [2, 0],
               |       |                                   [1, 2],
               1<----->2                                   [2, 1],
               |       |                                   [1, 3],
               v       v                                   [2, 4],
               3------>4                                   [3, 4],
               |                                           [3, 5]])
               v
               5

    copy : `bool`, optional
        If ``False``, the ``adjacency_list`` will not be copied on assignment.

    Raises
    ------
    ValueError
        You must provide at least one edge.
    ValueError
        Adjacency list must contain the sets of connected edges and thus must
        have shape (n_edges, 2).
    ValueError
        The vertices must be numbered starting from 0.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, adjacency_array, copy=True):
        # check that adjacency_array has expected shape
        if adjacency_array.size == 0:
            raise ValueError('You must provide at least one edge.')
        if adjacency_array.shape[1] != 2:
            raise ValueError('Adjacency list must contain the sets of '
                             'connected edges and thus must have shape '
                             '(n_edges, 2).')
        # check that numbering of vertices is zero-based
        if adjacency_array.min() != 0:
            raise ValueError('The vertices must be numbered starting from 0.')

        # keep unique rows of adjacency_array
        adjacency_array = _unique_array_rows(adjacency_array)

        if copy:
            self.adjacency_array = adjacency_array.copy()
        else:
            self.adjacency_array = adjacency_array
        self.adjacency_list = self._get_adjacency_list()

    @property
    def n_edges(self):
        r"""
        Returns the number of the graph's edges.

        :type: `int`
        """
        return self.adjacency_array.shape[0]

    @property
    def n_vertices(self):
        r"""
        Returns the number of the graph's vertices.

        :type: `int`
        """
        return self.adjacency_array.max() + 1

    @abc.abstractmethod
    def get_adjacency_matrix(self):
        r"""
        Returns the Adjacency Matrix of the graph, i.e. the boolean ndarray that
        with True and False if there is an edge connecting the two vertices or
        not respectively.

        :type: ``(n_vertices, n_vertices, )`` `ndarray`
        """
        pass

    @abc.abstractmethod
    def _get_adjacency_list(self):
        r"""
        Returns the Adjacency List of the graph, i.e. a list of length
        n_vertices that for each vertex has a list of the vertex neighbours.
        If the graph is directed, the neighbours are children.

        :type: `list` of `lists` of len n_vertices
        """
        pass

    def find_path(self, start, end, path=[]):
        r"""
        Returns a list with the first path (without cycles) found from start
        vertex to end vertex.

        Parameters
        ----------
        start : `int`
            The vertex from which the path starts.

        end : `int`
            The vertex from which the path ends.

        Returns
        -------
        path : `list`
            The path's vertices.
        """
        path = path + [start]
        if start == end:
            return path
        if start > self.n_vertices - 1 or start < 0:
            return None
        for v in self.adjacency_list[start]:
            if v not in path:
                newpath = self.find_path(v, end, path)
                if newpath:
                    return newpath
        return None

    def find_all_paths(self, start, end, path=[]):
        r"""
        Returns a list of lists with all the paths (without cycles) found from
        start vertex to end vertex.

        Parameters
        ----------
        start : `int`
            The vertex from which the paths start.

        end : `int`
            The vertex from which the paths end.

        Returns
        -------
        paths : `list` of `list`
            The list containing all the paths from start to end.
        """
        path = path + [start]
        if start == end:
            return [path]
        if start > self.n_vertices - 1 or start < 0:
            return []
        paths = []
        for v in self.adjacency_list[start]:
            if v not in path:
                newpaths = self.find_all_paths(v, end, path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

    def n_paths(self, start, end):
        r"""
        Returns the number of all the paths (without cycles) existing from
        start vertex to end vertex.

        Parameters
        ----------
        start : `int`
            The vertex from which the paths start.

        end : `int`
            The vertex from which the paths end.

        Returns
        -------
        paths : `int`
            The paths' numbers.
        """
        return len(self.find_all_paths(start, end))

    def find_shortest_path(self, start, end, path=[]):
        r"""
        Returns a list with the shortest path (without cycles) found from start
        vertex to end vertex.

        Parameters
        ----------
        start : `int`
            The vertex from which the path starts.

        end : `int`
            The vertex from which the path ends.

        Returns
        -------
        path : `list`
            The shortest path's vertices.
        """
        path = path + [start]
        if start == end:
            return path
        if start > self.n_vertices - 1 or start < 0:
            return None
        shortest = None
        for v in self.adjacency_list[start]:
            if v not in path:
                newpath = self.find_shortest_path(v, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    def has_cycles(self):
        r"""
        Checks if the graph has at least one cycle.
        """
        pass

    def is_tree(self):
        r"""
        Checks if the graph is tree.
        """
        return not self.has_cycles() and self.n_edges == self.n_vertices - 1

    def _check_vertex(self, vertex):
        r"""
        Checks that a given vertex is valid.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        if vertex > self.n_vertices - 1 or vertex < 0:
            raise ValueError('The vertex must be between '
                             '0 and {}.'.format(self.n_vertices-1))

    def tojson(self):
        r"""
        Convert the graph to a dictionary JSON representation.

        Returns
        -------
        dictionary with 'adjacency_array' key. Suitable or use in the by the
        `json` standard library package.
        """
        return {'adjacency_array': self.adjacency_array.tolist()}


class UndirectedGraph(Graph):
    r"""
    Class for Undirected Graph definition and manipulation.
    """
    def get_adjacency_matrix(self):
        adjacency_mat = np.zeros((self.n_vertices, self.n_vertices),
                                 dtype=np.bool)
        for e in range(self.n_edges):
            v1 = self.adjacency_array[e, 0]
            v2 = self.adjacency_array[e, 1]
            adjacency_mat[v1, v2] = True
            adjacency_mat[v2, v1] = True

        return adjacency_mat

    def _get_adjacency_list(self):
        adjacency_list = [[] for _ in range(self.n_vertices)]
        for e in range(self.n_edges):
            v1 = self.adjacency_array[e, 0]
            v2 = self.adjacency_array[e, 1]
            adjacency_list[v1].append(v2)
            adjacency_list[v2].append(v1)
        return adjacency_list

    def neighbours(self, vertex):
        r"""
        Returns the neighbours of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        neighbours : `list`
            The list of neighbours.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return self.adjacency_list[vertex]

    def n_neighbours(self, vertex):
        r"""
        Returns the number of neighbours of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        n_neighbours : `int`
            The number of neighbours.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return len(self.neighbours(vertex))

    def is_edge(self, vertex_1, vertex_2):
        r"""
        Returns whether there is an edge between the provided vertices.

        Parameters
        ----------
        vertex_1 : `int`
            The first selected vertex.

        vertex_2 : `int`
            The second selected vertex.

        Returns
        -------
        is_edge : `bool`
            True if there is an edge.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex_1)
        self._check_vertex(vertex_2)
        return (vertex_1 in self.adjacency_list[vertex_2] or
                vertex_2 in self.adjacency_list[vertex_1])

    def has_cycles(self):
        r"""
        Whether the graph has at least on cycle.

        Returns
        -------
        has_cycles : `bool`
            True if it has at least one cycle.
        """
        return _has_cycles(self.adjacency_list, False)

    def minimum_spanning_tree(self, weights, root_vertex):
        r"""
        Returns the minimum spanning tree given weights to the graph's edges
        using Kruskal's algorithm.

        Parameter
        ---------
        weights : ``(n_vertices, n_vertices, )`` `ndarray`
            A matrix of the same size as the adjacency matrix that attaches a
            weight to each edge of the undirected graph.

        root_vertex : `int`
            The vertex that will be set as root in the output MST.

        Returns
        -------
        mst : :class:`menpo.shape.Tree`
            The computed minimum spanning tree.

        Raises
        ------
        ValueError
            Provided graph is not an UndirectedGraph.
        ValueError
            Assymetric weights provided.
        """
        # compute the edges of the minimum spanning tree
        from menpo.external.PADS.MinimumSpanningTree import MinimumSpanningTree
        tree_edges = MinimumSpanningTree(self, weights)

        # Correct the tree edges so that they have the correct format
        # (i.e. ndarray of pairs in the form (parent, child)) using BFS
        tree_edges = _correct_tree_edges(tree_edges, root_vertex)

        return Tree(np.array(tree_edges), root_vertex)

    def __str__(self):
        return "Undirected graph of {} vertices and {} edges.".format(
            self.n_vertices, self.n_edges)


class DirectedGraph(Graph):
    r"""
    Class for Directed Graph definition and manipulation.
    """

    def get_adjacency_matrix(self):
        adjacency_mat = np.zeros((self.n_vertices, self.n_vertices),
                                 dtype=np.bool)
        for e in range(self.n_edges):
            parent = self.adjacency_array[e, 0]
            child = self.adjacency_array[e, 1]
            adjacency_mat[parent, child] = True
        return adjacency_mat

    def _get_adjacency_list(self):
        adjacency_list = [[] for _ in range(self.n_vertices)]
        for e in range(self.n_edges):
            parent = self.adjacency_array[e, 0]
            child = self.adjacency_array[e, 1]
            adjacency_list[parent].append(child)
        return adjacency_list

    def children(self, vertex):
        r"""
        Returns the children of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        children : `list`
            The list of children.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return self.adjacency_list[vertex]

    def n_children(self, vertex):
        r"""
        Returns the number of children of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        n_children : `int`
            The number of children.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return len(self.children(vertex))

    def parent(self, vertex):
        r"""
        Returns the parents of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        parent : `list`
            The list of parents.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        adj = self.get_adjacency_matrix()
        return list(np.where(adj[:, vertex])[0])

    def n_parent(self, vertex):
        r"""
        Returns the number of parents of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        n_parent : `int`
            The number of parents.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return len(self.parent(vertex))

    def is_edge(self, parent, child):
        r"""
        Returns whether there is an edge between the provided vertices.

        Parameters
        ----------
        parent : `int`
            The first selected vertex which is considered as the parent.

        child : `int`
            The second selected vertex which is considered as the child.

        Returns
        -------
        is_edge : `bool`
            True if there is an edge.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(parent)
        self._check_vertex(child)
        return child in self.adjacency_list[parent]

    def has_cycles(self):
        r"""
        Whether the graph has at least on cycle.

        Returns
        -------
        has_cycles : `bool`
            True if it has at least one cycle.
        """
        return _has_cycles(self.adjacency_list, True)

    def __str__(self):
        return "Directed graph of {} vertices and {} edges.".format(
            self.n_vertices, self.n_edges)


class Tree(DirectedGraph):
    r"""
    Class for Tree definitions and manipulation.

    Parameters
    -----------
    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the tree, i.e. an array containing the sets of
        the tree's edges. The numbering of vertices is assumed to start from 0.

        We assume that the vertices in the first column of the adjacency_array
        are the fathers and the vertices in the second column of the
        adjacency_array are the children, for example:

                   0            adjacency_array = ndarray([[0, 1],
                   |                                       [0, 2],
                ___|___                                    [1, 3],
               1       2                                   [1, 4],
               |       |                                   [2, 5],
              _|_      |                                   [3, 6],
             3   4     5                                   [4, 7],
             |   |     |                                   [5, 8]])
             |   |     |
             6   7     8

    root_vertex : `int`
        The vertex that will be considered as root.

    copy : `bool`, optional
        If ``False``, the ``adjacency_list`` will not be copied on assignment.

    Raises
    ------
    ValueError
        The provided edges do not represent a tree.
    ValueError
        The root_vertex must be between 0 and n_vertices-1.
    """
    def __init__(self, adjacency_array, root_vertex, copy=True):
        super(Tree, self).__init__(adjacency_array, copy=copy)
        # check if provided adjacency_array represents a tree
        if not (self.is_tree() and self.n_edges == self.n_vertices - 1):
            raise ValueError('The provided edges do not represent a tree.')
        # check if root_vertex is valid
        self._check_vertex(root_vertex)

        self.root_vertex = root_vertex
        self.predecessors_list = self._get_predecessors_list()

    def _get_predecessors_list(self):
        r"""
        Returns the Predecessors List of the tree, i.e. a list of length
        n_vertices that for each vertex it has its parent. The value of the
        root vertex is None.

        :type: `list` of len n_vertices
        """
        predecessors_list = [None] * self.n_vertices
        for e in range(self.n_edges):
            parent = self.adjacency_array[e, 0]
            child = self.adjacency_array[e, 1]
            predecessors_list[child] = parent
        return predecessors_list

    def depth_of_vertex(self, vertex):
        r"""
        Returns the depth of the specified vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        depth : `int`
            The depth of the selected vertex.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        parent = vertex
        depth = 0
        while not parent == self.root_vertex:
            current = parent
            parent = self.predecessors_list[current]
            depth += 1
        return depth

    @property
    def maximum_depth(self):
        r"""
        Returns the maximum depth of the tree.

        :type: `int`
        """
        all_depths = [self.depth_of_vertex(v) for v in range(self.n_vertices)]
        return np.max(all_depths)

    def vertices_at_depth(self, depth):
        r"""
        Returns a list of vertices at the specified depth.

        Parameter
        ---------
        depth : `int`
            The selected depth.

        Returns
        -------
        vertices : `list`
            The vertices that lie in the specified depth.
        """
        ver = []
        for v in range(self.n_vertices):
            if self.depth_of_vertex(v) == depth:
                ver.append(v)
        return ver

    def n_vertices_at_depth(self, depth):
        r"""
        Returns the number of vertices at the specified depth.

        Parameter
        ---------
        depth : `int`
            The selected depth.

        Returns
        -------
        n_vertices : `int`
            The number of vertices that lie in the specified depth.
        """
        n_ver = 0
        for v in range(self.n_vertices):
            if self.depth_of_vertex(v) == depth:
                n_ver += 1
        return n_ver

    def is_leaf(self, vertex):
        r"""
        Returns whether the vertex is a leaf.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        is_leaf : `bool`
            If True, then selected vertex is a leaf.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return len(self.children(vertex)) == 0

    @property
    def leaves(self):
        r"""
        Returns a list with the all leaves of the tree.

        :type: `list`
        """
        leaves = []
        for v in range(self.n_vertices):
            if self.is_leaf(v):
                leaves.append(v)
        return leaves

    @property
    def n_leaves(self):
        r"""
        Returns the number of leaves of the tree.

        :type: `int`
        """
        n_leaves = 0
        for v in range(self.n_vertices):
            if self.is_leaf(v):
                n_leaves += 1
        return n_leaves

    def parent(self, vertex):
        r"""
        Returns the parent of the selected vertex.

        Parameter
        ---------
        vertex : `int`
            The selected vertex.

        Returns
        -------
        parent : `int`
            The parent vertex.

        Raises
        ------
        ValueError
            The vertex must be between 0 and {n_vertices-1}.
        """
        self._check_vertex(vertex)
        return self.predecessors_list[vertex]

    def __str__(self):
        return "Tree of depth {} with {} vertices and {} leaves.".format(
            self.maximum_depth, self.n_vertices, self.n_leaves)


class PointGraph(object):
    r"""
    Class for defining a graph with geometry.

    Parameters
    -----------
    points : `ndarray`
        The array of point locations.

    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the graph, i.e. an array containing the sets of
        the graph's edges. The numbering of vertices is assumed to start from 0.

        For an undirected graph, the order of an edge's vertices doesn't matter,
        for example:
               |---0---|        adjacency_array = ndarray([[0, 1],
               |       |                                   [0, 2],
               |       |                                   [1, 2],
               1-------2                                   [1, 3],
               |       |                                   [2, 4],
               |       |                                   [3, 4],
               3-------4                                   [3, 5]])
               |
               5

        For a directed graph, we assume that the vertices in the first column of
        the adjacency_array are the fathers and the vertices in the second
        column of the adjacency_array are the children, for example:
               |-->0<--|        adjacency_array = ndarray([[1, 0],
               |       |                                   [2, 0],
               |       |                                   [1, 2],
               1<----->2                                   [2, 1],
               |       |                                   [1, 3],
               v       v                                   [2, 4],
               3------>4                                   [3, 4],
               |                                           [3, 5]])
               v
               5
    """
    def __init__(self, points, adjacency_array):
        _check_n_points(points, adjacency_array)

    def view(self, figure_id=None, new_figure=False, **kwargs):
        return PointGraphViewer(figure_id, new_figure,
                                self.points,
                                self.adjacency_array).render(**kwargs)


class PointUndirectedGraph(PointGraph, UndirectedGraph, PointCloud):
    r"""
    Class for defining an Undirected Graph with geometry.

    Parameters
    -----------
    points : `ndarray`
        The array of point locations.

    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the graph, i.e. an array containing the sets of
        the graph's edges. The numbering of vertices is assumed to start from 0.
        For example:
               |---0---|        adjacency_array = ndarray([[0, 1],
               |       |                                   [0, 2],
               |       |                                   [1, 2],
               1-------2                                   [1, 3],
               |       |                                   [2, 4],
               |       |                                   [3, 4],
               3-------4                                   [3, 5]])
               |
               5

    copy : `bool`, optional
        If ``False``, the ``adjacency_list`` will not be copied on assignment.

    Raises
    ------
    ValueError
        A point for each graph vertex needs to be passed. Got {n_points} points
        instead of {n_vertices}.
    """
    def __init__(self, points, adjacency_array, copy=True):
        super(PointUndirectedGraph, self).__init__(points, adjacency_array)
        UndirectedGraph.__init__(self, adjacency_array, copy=copy)
        PointCloud.__init__(self, points, copy=copy)

    def from_mask(self, mask):
        """
        A 1D boolean array with the same number of elements as the number of
        points in the PointUndirectedGraph. This is then broadcast across the
        dimensions of the PointUndirectedGraph and returns a new
        PointUndirectedGraph containing only those points that were ``True`` in
        the mask.

        Parameters
        ----------
        mask : ``(n_points,)`` `ndarray`
            1D array of booleans

        Returns
        -------
        pointgraph : :map:`PointUndirectedGraph`
            A new pointgraph that has been masked.

        Raises
        ------
        ValueError
            Mask must have same number of points as pointgraph.
        """
        if mask.shape[0] != self.n_points:
            raise ValueError('Mask must be a 1D boolean array of the same '
                             'number of entries as points in this '
                             'PointUndirectedGraph.')

        pg = self.copy()
        if np.all(mask):  # Shortcut for all true masks
            return pg
        else:
            masked_adj = mask_adjacency_array(mask, pg.adjacency_array)
            if len(masked_adj) == 0:
                raise ValueError('The provided mask deletes all edges.')
            pg.adjacency_array = reindex_adjacency_array(masked_adj)
            pg.adjacency_list = pg._get_adjacency_list()
            pg.points = pg.points[mask, :]
            return pg

    def tojson(self):
        r"""
        Convert this `PointUndirectedGraph` to a dictionary JSON representation.

        Returns
        -------
        dictionary with 'points' and 'adjacency_array' keys. Both are lists
        suitable or use in the by the `json` standard library package.
        """
        json_dict = PointCloud.tojson(self)
        json_dict.update(UndirectedGraph.tojson(self))
        return json_dict


class PointDirectedGraph(PointGraph, DirectedGraph, PointCloud):
    r"""
    Class for defining a Directed Graph with geometry.

    Parameters
    -----------
    points : `ndarray`
        The array of point locations.

    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the graph, i.e. an array containing the sets of
        the graph's edges. The numbering of vertices is assumed to start from 0.
        For example:
               |-->0<--|        adjacency_array = ndarray([[1, 0],
               |       |                                   [2, 0],
               |       |                                   [1, 2],
               1<----->2                                   [2, 1],
               |       |                                   [1, 3],
               v       v                                   [2, 4],
               3------>4                                   [3, 4],
               |                                           [3, 5]])
               v
               5

    copy : `bool`, optional
        If ``False``, the ``adjacency_list`` will not be copied on assignment.

    Raises
    ------
    ValueError
        A point for each graph vertex needs to be passed. Got {n_points} points
        instead of {n_vertices}.
    """
    def __init__(self, points, adjacency_array, copy=True):
        super(PointDirectedGraph, self).__init__(points, adjacency_array)
        DirectedGraph.__init__(self, adjacency_array, copy=copy)
        PointCloud.__init__(self, points, copy=copy)

    def relative_location_edge(self, parent, child):
        r"""
        Returns the relative location between the provided vertices. That is
        if vertex j is the parent and vertex i is its child and vector l
        denotes the coordinates of a vertex, then:

                    l_i - l_j = [[x_i], [y_i]] - [[x_j], [y_j]] =
                              = [[x_i - x_j], [y_i - y_j]]

        Parameters
        ----------
        parent : `int`
            The first selected vertex which is considered as the parent.

        child : `int`
            The second selected vertex which is considered as the child.

        Returns
        -------
        relative_location : `ndarray`
            The relative location vector.

        Raises
        ------
        ValueError
            Vertices {parent} and {child} are not connected with an edge.
        """
        if not self.is_edge(parent, child):
            raise ValueError('Vertices {} and {} are not connected '
                             'with an edge.'.format(parent, child))
        return self.points[child, ...] - self.points[parent, ...]

    def relative_locations(self):
        r"""
        Returns the relative location between the vertices of each edge. If
        vertex j is the parent and vertex i is its child and vector l denotes
        the coordinates of a vertex, then:

                    l_i - l_j = [[x_i], [y_i]] - [[x_j], [y_j]] =
                              = [[x_i - x_j], [y_i - y_j]]

        Returns
        -------
        relative_locations : `ndarray`
            The relative locations vector.
        """
        parents = [p[0] for p in self.adjacency_array]
        children = [p[1] for p in self.adjacency_array]
        return self.points[children] - self.points[parents]

    def from_mask(self, mask):
        """
        A 1D boolean array with the same number of elements as the number of
        points in the PointDirectedGraph. This is then broadcast across the
        dimensions of the PointDirectedGraph and returns a new
        PointDirectedGraph containing only those points that were ``True`` in
        the mask.

        Parameters
        ----------
        mask : ``(n_points,)`` `ndarray`
            1D array of booleans

        Returns
        -------
        pointgraph : :map:`PointDirectedGraph`
            A new pointgraph that has been masked.

        Raises
        ------
        ValueError
            Mask must have same number of points as pointgraph.
        """
        if mask.shape[0] != self.n_points:
            raise ValueError('Mask must be a 1D boolean array of the same '
                             'number of entries as points in this PointTree.')

        pt = self.copy()
        if np.all(mask):  # Shortcut for all true masks
            return pt
        else:
            masked_adj = mask_adjacency_array_tree(
                mask, pt.adjacency_array, pt.adjacency_list,
                pt.predecessors_list, pt.root_vertex)
            if len(masked_adj) == 0:
                raise ValueError('The provided mask deletes all edges.')
            pt.adjacency_array = reindex_adjacency_array(masked_adj)
            pt.points = pt.points[mask, :]
            pt.adjacency_list = pt._get_adjacency_list()
            pt.predecessors_list = pt._get_predecessors_list()
            return pt

    def tojson(self):
        r"""
        Convert this `PointDirectedGraph` to a dictionary JSON representation.

        Returns
        -------
        dictionary with 'points' and 'adjacency_array' keys. Both are lists
        suitable or use in the by the `json` standard library package.
        """
        json_dict = PointCloud.tojson(self)
        json_dict.update(DirectedGraph.tojson(self))
        return json_dict


class PointTree(PointDirectedGraph, Tree, PointCloud):
    r"""
    Class for defining a Tree with geometry.

    Parameters
    -----------
    points : `ndarray`
        The array of point locations.

    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The Adjacency Array of the tree, i.e. an array containing the sets of
        the tree's edges. The numbering of vertices is assumed to start from 0.

        We assume that the vertices in the first column of the adjacency_array
        are the fathers and the vertices in the second column of the
        adjacency_array are the children, for example:

                   0            adjacency_array = ndarray([[0, 1],
                   |                                       [0, 2],
                ___|___                                    [1, 3],
               1       2                                   [1, 4],
               |       |                                   [2, 5],
              _|_      |                                   [3, 6],
             3   4     5                                   [4, 7],
             |   |     |                                   [5, 8]])
             |   |     |
             6   7     8

    root_vertex : `int`
        The root vertex of the tree.

    copy : `bool`, optional
        If ``False``, the ``adjacency_list`` will not be copied on assignment.
    """
    def __init__(self, points, adjacency_array, root_vertex, copy=True):
        super(PointDirectedGraph, self).__init__(points, adjacency_array)
        Tree.__init__(self, adjacency_array, root_vertex, copy=copy)
        PointCloud.__init__(self, points, copy=copy)

    def from_mask(self, mask):
        """
        A 1D boolean array with the same number of elements as the number of
        points in the PointTree. This is then broadcast across the dimensions
        of the PointTree and returns a new PointTree containing only those
        points that were ``True`` in the mask.

        Parameters
        ----------
        mask : ``(n_points,)`` `ndarray`
            1D array of booleans

        Returns
        -------
        pointtree : :map:`PointTree`
            A new pointtree that has been masked.

        Raises
        ------
        ValueError
            Mask must have same number of points as pointtree.
        """
        if mask.shape[0] != self.n_points:
            raise ValueError('Mask must be a 1D boolean array of the same '
                             'number of entries as points in this PointTree.')

        pt = self.copy()
        if np.all(mask):  # Shortcut for all true masks
            return pt
        else:
            masked_adj = mask_adjacency_array_tree(
                mask, pt.adjacency_array, pt.adjacency_list,
                pt.predecessors_list, pt.root_vertex)
            if len(masked_adj) == 0:
                raise ValueError('The provided mask deletes all edges.')
            pt.adjacency_array = reindex_adjacency_array(masked_adj)
            pt.points = pt.points[mask, :]
            pt.adjacency_list = pt._get_adjacency_list()
            pt.predecessors_list = pt._get_predecessors_list()
            return pt

    def tojson(self):
        r"""
        Convert this `PointUndirectedGraph` to a dictionary JSON representation.

        Returns
        -------
        dictionary with 'points' and 'adjacency_array' keys. Both are lists
        suitable or use in the by the `json` standard library package.
        """
        json_dict = PointCloud.tojson(self)
        json_dict.update(UndirectedGraph.tojson(self))
        return json_dict


def _unique_array_rows(array):
    r"""
    Returns the unique rows of the given 2D ndarray.

    :type: `ndarray`
    """
    tmp = array.ravel().view(np.dtype((np.void,
                                       array.dtype.itemsize * array.shape[1])))
    _, unique_idx = np.unique(tmp, return_index=True)
    return array[np.sort(unique_idx)]


def _check_n_points(points, adjacency_array):
    r"""
    Checks whether the points array and the adjacency_array have the same number
    of points.
    """
    if not points.shape[0] == adjacency_array.max() + 1:
        raise ValueError('A point for each graph vertex needs to be '
                         'passed. Got {} points instead of {}'.format(
                         points.shape[0], adjacency_array.max() + 1))


def _correct_tree_edges(edges, root_vertex):
    def _get_children(p, e):
        c = []
        for m in e:
            if m.index(p) == 0:
                c.append(m[1])
            else:
                c.append(m[0])
        return c

    output_edges = []
    vertices_to_visit = [root_vertex]
    while len(vertices_to_visit) > 0:
        # get first vertex of list and remove it
        current_vertex = vertices_to_visit.pop(0)

        # find the edges containing the vertex
        current_edges = [item for item in edges if current_vertex in item]

        # remove the edges from the edges list
        for e in current_edges:
            edges.remove(e)

        # get the list of children of the vertex
        children = _get_children(current_vertex, current_edges)

        for child in children:
            # append the edge
            output_edges.append((current_vertex, child))

            # append the child
            vertices_to_visit.append(child)
    return output_edges


def _has_cycles(adjacency_list, directed):
    r"""
    Function that checks if the provided directed graph has cycles.

    Parameter
    ---------
    adjacency_array : ``(n_edges, 2, )`` `ndarray`
        The adjacency array of the directed graph.

    directed : `boolean`
        Defines if the provided graph is directed or not.
    """
    def dfs(node, entered, exited, tree_edges, back_edges):
        if node not in entered:
            entered.add(node)
            for y in adjacency_list[node]:
                if y not in entered:
                    tree_edges[y] = node
                elif (not directed and tree_edges.get(node, None) != y
                      or directed and y not in exited):
                    back_edges.setdefault(y, set()).add(node)
                dfs(y, entered, exited, tree_edges, back_edges)
            exited.add(node)
        return tree_edges, back_edges
    for x in range(len(adjacency_list)):
        if dfs(x, entered=set(), exited=set(), tree_edges={}, back_edges={})[1]:
            return True
    else:
        return False
