# Imports from libraries
import os
import pickle
from pytups import SuperDict, TupList


# Imports from cornflow libraries
from cornflow_client import InstanceCore
from cornflow_client.core.tools import load_json
import gurobipy as gp
from ..scripts.read_data import read_data
import time


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))

    def __init__(self, name, input_folder):
        self.name = name
        self.input_folder = input_folder
        self.lots = list()
        self.sites = list()
        self.nodes = list()
        self.cells = list()
        self.existing_sites = list()
        self.potential_sites = list()
        self.initial_capacity = dict()
        self.max_capacity = dict()
        self.demand = dict()
        self.coverage = list()
        self.existing_node_in_site = list()
        self.potential_node_in_site = list()
        self.existing_cell_in_site_node = list()
        self.potential_cell_in_site_node = list()
        self.site_cells_lighting_lot_node = list()
        self.lots_covered_by_site_node_cell = list()
        self.model = gp.Model("network_dimensioning")
        self.solver_params = dict()
        self.read_data()

    def read_data(self):
        print("Reading data")
        start_time = time.time()

        (
            self.lots,
            self.sites,
            self.nodes,
            self.cells,
            self.existing_sites,
            self.potential_sites,
            self.initial_capacity,
            self.max_capacity,
            self.demand,
            self.coverage,
            self.existing_node_in_site,
            self.potential_node_in_site,
            self.existing_cell_in_site_node,
            self.potential_cell_in_site_node,
            self.site_cells_lighting_lot_node,
            self.lots_covered_by_site_node_cell,
        ) = read_data(self.input_folder)

        print("Data read. Time: {}".format(time.time() - start_time))
