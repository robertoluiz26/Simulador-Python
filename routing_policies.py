import abc
import typing
import numpy as np
from typing import Tuple, Optional
import random
if typing.TYPE_CHECKING:
    from core import Service
    from graph import Path
    from networkx import Graph


class RoutingPolicy(abc.ABC):

    def __init__(self):
        self.env = None
        self.name = None

    @abc.abstractmethod
    def route(self, service: 'Service') -> Tuple[bool, str, 'Path']:
        pass

class ClosestAvailableDC(RoutingPolicy):

    def __init__(self):
        super().__init__()
        self.name = 'CADC'

    def route(self, service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the closest DC with enough available CPUs and with a path with enough available network resources
        """
        found = False
        closest_path_hops = np.finfo(0.0).max  # initializes load to the maximum value of a float
        closest_dc = None
        closest_path = None
        for iddc, dc in enumerate(self.env.topology.graph['dcs']):
            if self.env.topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = self.env.topology.graph['ksp'][service.source, dc] #Pegar o service.dest ao inves do source
                for idp, path in enumerate(paths):
                    if is_path_viable(self.env.topology, path, service.network_units) and closest_path_hops > path.hops:
                        closest_path_hops = path.hops
                        closest_dc = dc
                        closest_path = path
                        found = True
        return found, closest_dc, closest_path  # returns false and an index out of bounds if no path is available
class RandomAvailableDC(RoutingPolicy):

    def __init__(self):
        super().__init__()
        self.name = 'RADC'

    def route(self, service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the closest DC with enough available CPUs and with a path with enough available network resources
        """
        found = False
        closest_path_hops = np.finfo(0.0).max  # initializes load to the maximum value of a float
        closest_dc = None
        closest_path = None
        dc_list  = self.env.topology.graph['dcs'].copy()
        while(len(dc_list)>0 and found == False):
            dc = random.choice(dc_list)
            for d in dc_list:
                if d == dc:
                    dc_list.remove(d)
            if self.env.topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = self.env.topology.graph['ksp'][service.source, dc]
                for idp, path in enumerate(paths):
                    if is_path_viable(self.env.topology, path, service.network_units) and closest_path_hops > path.hops:
                        closest_path_hops = path.hops
                        closest_dc = dc
                        closest_path = path
                if(closest_path!=None):
                    found = True
        return found, closest_dc, closest_path  # returns false and an index out of bounds if no path is available

class FarthestAvailableDC(RoutingPolicy):

    def __init__(self):
        super().__init__()
        self.name = 'FADC'

    def route(self, service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the farthest DC with enough available CPUs and with a path with enough available network resources
        """
        found = False
        farthest_path_hops = 0.0  # initializes load to the maximum value of a float
        farthest_dc = None
        farthest_path = None
        for iddc, dc in enumerate(self.env.topology.graph['dcs']):
            if self.env.topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = self.env.topology.graph['ksp'][service.source, dc]
                for idp, path in enumerate(paths):
                    if is_path_viable(self.env.topology, path, service.network_units) and farthest_path_hops < path.hops:
                        farthest_path_hops = path.hops
                        farthest_dc = dc
                        farthest_path = path
                        found = True
        return found, farthest_dc, farthest_path  # returns false and an index out of bounds if no path is available


class FullLoadBalancing(RoutingPolicy):

    def __init__(self):
        super().__init__()
        self.name = 'FLB'

    def route(self, service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        found = False
        lowest_load = np.finfo(0.0).max  # initializes load to the maximum value of a float
        closest_dc = None
        closest_path = None
        for iddc, dc in enumerate(self.env.topology.graph['dcs']):
            if self.env.topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = self.env.topology.graph['ksp'][service.source, dc]
                for idp, path in enumerate(paths):
                    load = (get_max_usage(self.env.topology, path) / self.env.resource_units_per_link) * \
                           ((self.env.topology.nodes[dc]['total_units'] - self.env.topology.nodes[dc]['available_units']) /
                            self.env.topology.nodes[dc]['total_units'])
                    if is_path_viable(self.env.topology, path, service.network_units) and load < lowest_load:
                        lowest_load = load
                        closest_dc = dc
                        closest_path = path
                        found = True
        return found, closest_dc, closest_path  # returns false and an index out of bounds if no path is available


def is_path_viable(topology: 'Graph', path: 'Path', number_network_units: int) -> bool:
    for node in path.node_list:
        if topology.nodes[node]['failed']:
            return False
    for i in range(len(path.node_list) - 1):
        if topology[path.node_list[i]][path.node_list[i + 1]]['failed'] \
            or topology[path.node_list[i]][path.node_list[i + 1]]['available_units'] < number_network_units:
            return False
    return True


def get_max_usage(topology: 'Graph', path: 'Path') -> int:
    """
    Obtains the maximum usage of resources among all the links forming the path
    """
    max_usage = np.finfo(0.0).min
    for i in range(len(path.node_list) - 1):
        max_usage = max(max_usage, topology[path.node_list[i]][path.node_list[i + 1]]['total_units'] - topology[path.node_list[i]][path.node_list[i + 1]]['available_units'])
    return max_usage

def get_path_risk(topology: 'Graph', path: 'Path'):
    aecl:float = 0.0
    for i in range(len(path.node_list) - 1):
        x = topology[path.node_list[i]][path.node_list[i + 1]]['current_failure_probability']
        y = topology[path.node_list[i]][path.node_list[i+1]]['total_units']
        aecl += topology[path.node_list[i]][path.node_list[i + 1]]['current_failure_probability'] * topology[path.node_list[i]][path.node_list[i+1]]['total_units']
        #aecl += topology[path.node_list[i]][path.node_list[i+1]]['total_units']
        #print(topology[path.node_list[i]][path.node_list[i + 1]]['link_failure_probability'])
        #print(topology[path.node_list[i]][path.node_list[i + 1]]['total_units'])
    return (aecl / (len(path.node_list) - 1))

def get_shortest_path(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path = None
    closest_path_hops = np.finfo(0.0).max
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        paths = topology.graph['ksp'][service.source, service.destination]
        for path in paths:
            if is_path_viable(topology, path, service.network_units) and closest_path_hops > path.hops:
                closest_path_hops = path.hops
                closest_path = path
    return closest_path

def get_safest_path(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path_hops = np.finfo(0.0).max
    safest_path = None
    safest_path_risk = 100.0
    viable_paths = []
    prob_list = [0.73, 0.15, 0.05, 0]
    aux_list = [0,0,0,0]
    aux_dict = []
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        #paths = topology.graph['prob_ksp'][service.source, service.destination]
        paths = topology.graph['ksp'][service.source, service.destination]
        print(len(paths))
        
        for p in paths:
            if(is_path_viable(topology, p, service.network_units)):
                viable_paths.append(p)
        
        for i, path in enumerate(viable_paths):
            print("\n")
            aux_list = [0,0,0,0,0]
            aux_list[4] = i
            for j in range(len(path.node_list)-1):
                for idx, prob in enumerate(prob_list):
                    if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                        aux_list[idx]+=1
                
            aux_dict.append(aux_list)
        aux_dict.sort()

        if len(aux_dict) >0:
            print(aux_dict)
            safest_path_aux_list = aux_dict[0]
            safest_path = viable_paths[safest_path_aux_list[4]]
        else:
            safest_path = None
    
        '''
        for path in paths:
            print("get safest path hops")
            
            new_path_risk = get_path_risk(topology, path)
            print("Anterior: ", new_path_risk)
            if is_path_viable(topology, path, service.network_units) and safest_path_risk > new_path_risk:
                print (new_path_risk)
                closest_path_hops = path.hops
                safest_path_risk = new_path_risk
                safest_path = path
        '''
    #print(safest_path_risk)
    return safest_path

def get_safest_dc(topology: 'Graph', service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        prob_list = [0.73, 0.15, 0.05, 0]
        aux_list = [0,0,0,0]
        aux_dict = []
        found = False
        lowest_risk = [1,0,0,0]
        safest_path = None
        safest_dc = None
        for iddc, dc in enumerate(topology.graph['dcs']):
            if topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = topology.graph['ksp'][service.source, dc]
                for idp, path in enumerate(paths):
                    aux_list = [0,0,0,0]
                    for j in range(len(path.node_list)-1):
                        for idx, prob in enumerate(prob_list):
                            if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                                aux_list[idx]+=1
                    risk = aux_list.copy()
                    if is_path_viable(topology, path, service.network_units) and risk < lowest_risk:
                        lowest_risk=risk.copy()
                        safest_dc = dc
                        safest_path = path
                        found = True
                        print("Lowest risk::", lowest_risk)
                        print("Safest DC::", safest_dc)
                        print(".")
        return found, safest_dc, safest_path  # returns false and an index out of bounds if no path is available

def get_balanced_safest_dc(topology: 'Graph', service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        prob_list = [0.73, 0.15, 0.05, 0]
        aux_list = [0,0,0,0]
        aux_dict = []
        found = False
        lowest_risk = [1,0,0,0]
        safest_path = None
        safest_dc = None
        f_var: float = None
        lowest_f_var: float = 100
        highest_prob: float = 0.0
        max_hops = 0
        path_hops = 0
        for iddc, dc in enumerate(topology.graph['dcs']):
            if topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = topology.graph['ksp'][service.source, dc]

                for path in paths:
                    path_hops = (len(path.node_list)-1)
                    if path_hops > max_hops:
                        max_hops = path_hops

                    
                for idp, path in enumerate(paths):
                    aux_list = [0,0,0,0]
                    highest_prob = 0
                    prob = 0            
                    f_var = 0
                    for j in range(len(path.node_list)-1):
                        #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        if prob > highest_prob:
                            highest_prob = prob
                        
                    #mean_prob = prob/(len(path.node_list)-1)

                    for j in range(len(path.node_list)-1):
                        for idx, prob in enumerate(prob_list):
                            if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                                aux_list[idx]+=1
                                #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
                                f_var = (0.5*((len(path.node_list)-1)/max_hops))+(0.5*highest_prob)
                                #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)
                    risk = aux_list.copy()
                    if is_path_viable(topology, path, service.network_units) and f_var < lowest_f_var:
                        lowest_risk=risk.copy()
                        lowest_f_var = f_var
                        safest_dc = dc
                        safest_path = path
                        found = True
                        print("Lowest risk::", lowest_risk)
                        print("Safest DC::", safest_dc)
                        print(".")
        return found, safest_dc, safest_path  # returns false and an index out of bounds if no path is available

def get_balanced_sasfest_path(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path_hops = np.finfo(0.0).max
    safest_path = None
    safest_path_risk = 100.0
    viable_paths = []
    prob_list = [0.73, 0.15, 0.05, 0]
    aux_list = [0,0,0,0,0,0]
    aux_dict = []
    max_hops = 0
    f_var: float = 0.0
    f_idx_list =[0,0]
    num_hops: int = 0
    f_max: float = 100
    highest_prob = 0
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        #paths = topology.graph['prob_ksp'][service.source, service.destination]
        paths = topology.graph['ksp'][service.source, service.destination]
        
        for p in paths:
            num_hops = 0
            if(is_path_viable(topology, p, service.network_units)):
                viable_paths.append(p)
                num_hops = (len(p.node_list)-1)
                if(num_hops>max_hops):
                    max_hops = num_hops
            

        for i, path in enumerate(viable_paths):
            prob = 0
            highest_prob = 0
            for j in  range(len(path.node_list)-1):
                #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                
                prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                if prob > highest_prob:
                    highest_prob = prob
            #mean_prob = prob/(len(path.node_list)-1)

            aux_list = [0,0,0,0,0,0]
            aux_list[4] = i  #Saves the Index in viable_paths list for further use
            for j in range(len(path.node_list)-1):
                for idx, prob in enumerate(prob_list):
                    if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                        aux_list[idx]+=1
            #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
            f_var = (0.5*((len(path.node_list)-1)/max_hops))+(0.5*highest_prob)
            #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)

            aux_list[5] = f_var #Saves f variable in index 5 of list
            aux_dict.append(aux_list)

        for idx, l in enumerate(aux_dict):
            if l[5] < f_max:
                f_max = l[5]
                safest_path_aux_list = aux_dict[idx]
                
        if len(viable_paths) >0:
            safest_path = viable_paths[safest_path_aux_list[4]]
        else:
            safest_path = None

    return safest_path

def get_dc_alfa_04(topology: 'Graph', service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        prob_list = [0.73, 0.15, 0.05, 0]
        aux_list = [0,0,0,0]
        aux_dict = []
        found = False
        lowest_risk = [1,0,0,0]
        safest_path = None
        safest_dc = None
        f_var: float = None
        lowest_f_var: float = 100
        highest_prob: float = 0.0
        max_hops = 0
        path_hops = 0
        for iddc, dc in enumerate(topology.graph['dcs']):
            if topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = topology.graph['ksp'][service.source, dc]

                for path in paths:
                    path_hops = (len(path.node_list)-1)
                    if path_hops > max_hops:
                        max_hops = path_hops

                    
                for idp, path in enumerate(paths):
                    aux_list = [0,0,0,0]
                    highest_prob = 0
                    prob = 0            
                    f_var = 0
                    for j in range(len(path.node_list)-1):
                        #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        if prob > highest_prob:
                            highest_prob = prob
                        
                    #mean_prob = prob/(len(path.node_list)-1)

                    for j in range(len(path.node_list)-1):
                        for idx, prob in enumerate(prob_list):
                            if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                                aux_list[idx]+=1
                                #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
                                f_var = (0.6*((len(path.node_list)-1)/max_hops))+(0.4*highest_prob)
                                #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)
                    risk = aux_list.copy()
                    if is_path_viable(topology, path, service.network_units) and f_var < lowest_f_var:
                        lowest_risk=risk.copy()
                        lowest_f_var = f_var
                        safest_dc = dc
                        safest_path = path
                        found = True
                        print("Lowest risk::", lowest_risk)
                        print("Safest DC::", safest_dc)
                        print(".")
        return found, safest_dc, safest_path  # returns false and an index out of bounds if no path is available

def get_path_alfa_04(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path_hops = np.finfo(0.0).max
    safest_path = None
    safest_path_risk = 100.0
    viable_paths = []
    prob_list = [0.73, 0.15, 0.05, 0]
    aux_list = [0,0,0,0,0,0]
    aux_dict = []
    max_hops = 0
    f_var: float = 0.0
    f_idx_list =[0,0]
    num_hops: int = 0
    f_max: float = 100
    highest_prob = 0
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        #paths = topology.graph['prob_ksp'][service.source, service.destination]
        paths = topology.graph['ksp'][service.source, service.destination]
        
        for p in paths:
            num_hops = 0
            if(is_path_viable(topology, p, service.network_units)):
                viable_paths.append(p)
                num_hops = (len(p.node_list)-1)
                if(num_hops>max_hops):
                    max_hops = num_hops
            

        for i, path in enumerate(viable_paths):
            prob = 0
            highest_prob = 0
            for j in  range(len(path.node_list)-1):
                #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                
                prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                if prob > highest_prob:
                    highest_prob = prob
            #mean_prob = prob/(len(path.node_list)-1)

            aux_list = [0,0,0,0,0,0]
            aux_list[4] = i  #Saves the Index in viable_paths list for further use
            for j in range(len(path.node_list)-1):
                for idx, prob in enumerate(prob_list):
                    if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                        aux_list[idx]+=1
            #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
            f_var = (0.6*((len(path.node_list)-1)/max_hops))+(0.4*highest_prob)
            #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)

            aux_list[5] = f_var #Saves f variable in index 5 of list
            aux_dict.append(aux_list)

        for idx, l in enumerate(aux_dict):
            if l[5] < f_max:
                f_max = l[5]
                safest_path_aux_list = aux_dict[idx]
                
        if len(viable_paths) >0:
            safest_path = viable_paths[safest_path_aux_list[4]]
        else:
            safest_path = None

    return safest_path

def get_dc_alfa_03(topology: 'Graph', service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        prob_list = [0.73, 0.15, 0.05, 0]
        aux_list = [0,0,0,0]
        aux_dict = []
        found = False
        lowest_risk = [1,0,0,0]
        safest_path = None
        safest_dc = None
        f_var: float = None
        lowest_f_var: float = 100
        highest_prob: float = 0.0
        max_hops = 0
        path_hops = 0
        for iddc, dc in enumerate(topology.graph['dcs']):
            if topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = topology.graph['ksp'][service.source, dc]

                for path in paths:
                    path_hops = (len(path.node_list)-1)
                    if path_hops > max_hops:
                        max_hops = path_hops

                    
                for idp, path in enumerate(paths):
                    aux_list = [0,0,0,0]
                    highest_prob = 0
                    prob = 0            
                    f_var = 0
                    for j in range(len(path.node_list)-1):
                        #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        if prob > highest_prob:
                            highest_prob = prob
                        
                    #mean_prob = prob/(len(path.node_list)-1)

                    for j in range(len(path.node_list)-1):
                        for idx, prob in enumerate(prob_list):
                            if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                                aux_list[idx]+=1
                                #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
                                f_var = (0.7*((len(path.node_list)-1)/max_hops))+(0.3*highest_prob)
                                #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)
                    risk = aux_list.copy()
                    if is_path_viable(topology, path, service.network_units) and f_var < lowest_f_var:
                        lowest_risk=risk.copy()
                        lowest_f_var = f_var
                        safest_dc = dc
                        safest_path = path
                        found = True
                        print("Lowest risk::", lowest_risk)
                        print("Safest DC::", safest_dc)
                        print(".")
        return found, safest_dc, safest_path  # returns false and an index out of bounds if no path is available

def get_path_alfa_03(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path_hops = np.finfo(0.0).max
    safest_path = None
    safest_path_risk = 100.0
    viable_paths = []
    prob_list = [0.73, 0.15, 0.05, 0]
    aux_list = [0,0,0,0,0,0]
    aux_dict = []
    max_hops = 0
    f_var: float = 0.0
    f_idx_list =[0,0]
    num_hops: int = 0
    f_max: float = 100
    highest_prob = 0
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        #paths = topology.graph['prob_ksp'][service.source, service.destination]
        paths = topology.graph['ksp'][service.source, service.destination]
        
        for p in paths:
            num_hops = 0
            if(is_path_viable(topology, p, service.network_units)):
                viable_paths.append(p)
                num_hops = (len(p.node_list)-1)
                if(num_hops>max_hops):
                    max_hops = num_hops
            

        for i, path in enumerate(viable_paths):
            prob = 0
            highest_prob = 0
            for j in  range(len(path.node_list)-1):
                #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                
                prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                if prob > highest_prob:
                    highest_prob = prob
            #mean_prob = prob/(len(path.node_list)-1)

            aux_list = [0,0,0,0,0,0]
            aux_list[4] = i  #Saves the Index in viable_paths list for further use
            for j in range(len(path.node_list)-1):
                for idx, prob in enumerate(prob_list):
                    if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                        aux_list[idx]+=1
            #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
            f_var = (0.7*((len(path.node_list)-1)/max_hops))+(0.3*highest_prob)
            #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)

            aux_list[5] = f_var #Saves f variable in index 5 of list
            aux_dict.append(aux_list)

        for idx, l in enumerate(aux_dict):
            if l[5] < f_max:
                f_max = l[5]
                safest_path_aux_list = aux_dict[idx]
                
        if len(viable_paths) >0:
            safest_path = viable_paths[safest_path_aux_list[4]]
        else:
            safest_path = None

    return safest_path
def get_dc_alfa_01(topology: 'Graph', service: 'Service') -> Tuple[bool, str, 'Path']:
        """
        Finds the path+DC pair with lowest combined load
        """
        prob_list = [0.73, 0.15, 0.05, 0]
        aux_list = [0,0,0,0]
        aux_dict = []
        found = False
        lowest_risk = [1,0,0,0]
        safest_path = None
        safest_dc = None
        f_var: float = None
        lowest_f_var: float = 100
        highest_prob: float = 0.0
        max_hops = 0
        path_hops = 0
        for iddc, dc in enumerate(topology.graph['dcs']):
            if topology.nodes[dc]['available_units'] >= service.computing_units:
                paths = topology.graph['ksp'][service.source, dc]

                for path in paths:
                    path_hops = (len(path.node_list)-1)
                    if path_hops > max_hops:
                        max_hops = path_hops

                    
                for idp, path in enumerate(paths):
                    aux_list = [0,0,0,0]
                    highest_prob = 0
                    prob = 0            
                    f_var = 0
                    for j in range(len(path.node_list)-1):
                        #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                        if prob > highest_prob:
                            highest_prob = prob
                        
                    #mean_prob = prob/(len(path.node_list)-1)

                    for j in range(len(path.node_list)-1):
                        for idx, prob in enumerate(prob_list):
                            if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                                aux_list[idx]+=1
                                #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
                                f_var = (0.9*((len(path.node_list)-1)/max_hops))+(0.1*highest_prob)
                                #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)
                    risk = aux_list.copy()
                    if is_path_viable(topology, path, service.network_units) and f_var < lowest_f_var:
                        lowest_risk=risk.copy()
                        lowest_f_var = f_var
                        safest_dc = dc
                        safest_path = path
                        found = True
                        print("Lowest risk::", lowest_risk)
                        print("Safest DC::", safest_dc)
                        print(".")
        return found, safest_dc, safest_path  # returns false and an index out of bounds if no path is available

def get_path_alfa_01(topology: 'Graph', service: 'Service') -> Optional['Path']:
    if service.destination is None:
        raise ValueError(f"Service should have value for destination, got {service}")
    closest_path_hops = np.finfo(0.0).max
    safest_path = None
    safest_path_risk = 100.0
    viable_paths = []
    prob_list = [0.73, 0.15, 0.05, 0]
    aux_list = [0,0,0,0,0,0]
    aux_dict = []
    max_hops = 0
    f_var: float = 0.0
    f_idx_list =[0,0]
    num_hops: int = 0
    f_max: float = 100
    highest_prob = 0
    if topology.nodes[service.destination]['available_units'] >= service.computing_units:
        #paths = topology.graph['prob_ksp'][service.source, service.destination]
        paths = topology.graph['ksp'][service.source, service.destination]
        
        for p in paths:
            num_hops = 0
            if(is_path_viable(topology, p, service.network_units)):
                viable_paths.append(p)
                num_hops = (len(p.node_list)-1)
                if(num_hops>max_hops):
                    max_hops = num_hops
            

        for i, path in enumerate(viable_paths):
            prob = 0
            highest_prob = 0
            for j in  range(len(path.node_list)-1):
                #prob += float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                
                prob = float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability'])
                if prob > highest_prob:
                    highest_prob = prob
            #mean_prob = prob/(len(path.node_list)-1)

            aux_list = [0,0,0,0,0,0]
            aux_list[4] = i  #Saves the Index in viable_paths list for further use
            for j in range(len(path.node_list)-1):
                for idx, prob in enumerate(prob_list):
                    if float(topology[path.node_list[j]][path.node_list[j+1]]['current_failure_probability']) == prob:
                        aux_list[idx]+=1
            #f_var = (0.95*((len(path.node_list)-1)/max_hops))+(highest_prob*0.05)
            f_var = (0.9*((len(path.node_list)-1)/max_hops))+(0.1*highest_prob)
            #f_var = (((len(path.node_list)-1)/max_hops))+(highest_prob)

            aux_list[5] = f_var #Saves f variable in index 5 of list
            aux_dict.append(aux_list)

        for idx, l in enumerate(aux_dict):
            if l[5] < f_max:
                f_max = l[5]
                safest_path_aux_list = aux_dict[idx]
                
        if len(viable_paths) >0:
            safest_path = viable_paths[safest_path_aux_list[4]]
        else:
            safest_path = None

    return safest_path
