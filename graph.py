from itertools import islice
from operator import itemgetter
import math
from xml.dom.minidom import parse
import xml.dom.minidom
import networkx as nx
import numpy as np
import xml.etree.ElementTree as ET



def get_k_shortest_paths(graph, source, target, k, weight=None):
    """
    Method from https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html#networkx.algorithms.simple_paths.shortest_simple_paths
    """
    print("teste ksp")
    return list(islice(nx.shortest_simple_paths(graph, source, target, weight=weight), k))

def get_k_safest_paths(graph, source, target, k, weight=None):
#def get_k_safest_paths(graph, source, target, k, weight='link_failure_probability'): 
    """
    Method from https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html#networkx.algorithms.simple_paths.shortest_simple_paths
    """
    print("graph:get_k_safest_paths")
    print(source, "--", target)
    return list(islice(nx.shortest_simple_paths(graph, source, target, weight='link_failure_probability'), k))
    #return list(islice(nx.shortest_simple_paths(graph, source, target, weight=weight), k))

def get_path_weight(graph, path, weight):
    return np.sum([graph[path[i]][path[i+1]][weight] for i in range(len(path) - 1)])

class Path:

    def __init__(self, node_list, length):
        self.node_list = node_list
        self.length = length
        self.hops = len(node_list) - 1


def calculate_geographical_distance(latlong1, latlong2):
    R = 6373.0

    lat1 = math.radians(latlong1[0])
    lon1 = math.radians(latlong1[1])
    lat2 = math.radians(latlong2[0])
    lon2 = math.radians(latlong2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    length = R * c
    return length


def read_sndlib_topology(file):
    graph = nx.Graph()

    with open('config/topologies/' + file) as file:
        tree = xml.dom.minidom.parse(file)
        document = tree.documentElement

        graph.graph["coordinatesType"] = document.getElementsByTagName("nodes")[0].getAttribute("coordinatesType")

        nodes = document.getElementsByTagName("node")
        for node in nodes:
            x = node.getElementsByTagName("x")[0]
            y = node.getElementsByTagName("y")[0]
            graph.add_node(node.getAttribute("id"), pos=((float(x.childNodes[0].data), float(y.childNodes[0].data))), failed=False)
        links = document.getElementsByTagName("link")
        for idx, link in enumerate(links):
            source = link.getElementsByTagName("source")[0]
            target = link.getElementsByTagName("target")[0]

            if graph.graph["coordinatesType"] == "geographical":
                length = np.around(calculate_geographical_distance(graph.nodes[source.childNodes[0].data]["pos"], graph.nodes[target.childNodes[0].data]["pos"]), 3)
            else:
                latlong1 = graph.nodes[source.childNodes[0].data]["pos"]
                latlong2 = graph.nodes[target.childNodes[0].data]["pos"]
                length = np.around(math.sqrt((latlong1[0] - latlong2[0]) ** 2 + (latlong1[1] - latlong2[1]) ** 2), 3)
            
            weight = 1.0
            graph.add_edge(source.childNodes[0].data, target.childNodes[0].data,
                           id=link.getAttribute("id"), weight=weight, length=length, index=idx,
                           failed=False)
    graph.graph["node_indices"] = []
    for idx, node in enumerate(graph.nodes()):
        graph.graph["node_indices"].append(node)

    for idx, lnk in enumerate(graph.edges()):
        graph[lnk[0]][lnk[1]]['link_failure_probability'] = 0
    return graph


def read_txt_file(file, topology_name):
    graph = nx.Graph(name=topology_name)
    nNodes = 0
    nLinks = 0
    with open('config/topologies/' + file, 'r') as nodes_lines:
        for idx, line_full in enumerate(nodes_lines):
            if "#" in line_full:
                line = line_full.split("#")[0].strip()
            else:
                line = line_full.strip()
            if idx > 2 and idx <= nNodes + 2: # skip title line
                info = line.replace("\n", "").replace(',', '.').split("\t")
                graph.add_node(info[0], name=info[1], pos=(float(info[2]), float(info[3])))
            elif idx > 2 + nNodes and idx <= 2 + nNodes + nLinks: # skip title line
                info = line.replace("\n", "").split("\t")
                n1 = graph.nodes[info[1]]
                n2 = graph.nodes[info[2]]
                dist = calculate_geographical_distance(n1['pos'], n2['pos'])
                # print(n1['name'], n1['pos'], n2['name'], n2['pos'], '{:.2f}'.format(dist), info[3])
                final_distance = float('{:.2f}'.format(max(dist, float(info[3]))))
                graph.add_edge(info[1], info[2], id=int(info[0]), weight=1.0, length=final_distance, index=idx-2, failed=False)
            elif idx == 1:
                nNodes = int(line)
            elif idx == 2:
                nLinks = int(line)
    return graph


def get_topology(args):
    if args.topology_file.endswith('.xml'):
        topology = read_sndlib_topology(args.topology_file)
    elif args.topology_file.endswith('.txt'):
        topology = read_txt_file(args.topology_file, args.topology_file.replace(".txt", ""))
    else:
        raise ValueError(f'Supplied topology  `{args.topology_file}` is unknown')
    topology = set_failure_probabilities(args, topology)
    return topology

def get_dcs(args, topology):
    topology.graph['source_nodes'] = []
    topology.graph['dcs'] = []
    if args.dc_placement == 'degree':
        degree = sorted(topology.degree(), key=itemgetter(1), reverse=True)
        for i in range(args.num_dcs):
            node = degree[i][0]
            topology.graph['dcs'].append(node)
            topology.nodes[node]['dc'] = True
            print(node)

        print(topology.graph['dcs'])
        for i in range(args.num_dcs, topology.number_of_nodes()):
            node = degree[i][0]
            topology.graph['source_nodes'].append(node)
            topology.nodes[node]['dc'] = False
        return topology

    if args.dc_placement == "fixed":  # fixed positions
        #,"Seattle", "San_Francisco",  "Denver",   "Charleston", "Ithaca" ,"Los_Angeles","New_Orleans", "Washington_DC", "El_Paso","Columbus" " 
        dc_nodes = ["Salt_Lake_City", "Birmingham", "Bismarck"]  # list of datacenters
        for node in topology.nodes():  # iterate over all nodes
            if node in dc_nodes:
                topology.graph['dcs'].append(node)
                topology.nodes[node]['dc'] = True
            else:
                topology.graph['source_nodes'].append(node)
                topology.nodes[node]['dc'] = False
        return topology
    else:
        raise ValueError('Selected args.dc_placement not correct!')


def get_ksp(args, topology):
    print("teste passagem ksp")
    k_shortest_paths = {}

    for idn1, n1 in enumerate(topology.graph['source_nodes']):
        for idn2, n2 in enumerate(topology.graph['dcs']):
            paths = get_k_shortest_paths(topology, n1, n2, args.k_paths)
            lengths = [get_path_weight(topology, path, 'length') for path in paths]
            objs = []
            for path, length in zip(paths, lengths):
                objs.append(Path(path, length))
            # both directions have the same paths, i.e., bidirectional symmetrical links
            k_shortest_paths[n1, n2] = objs
            k_shortest_paths[n2, n1] = objs
    topology.graph['ksp'] = k_shortest_paths
    return topology

def get_probability_ksp(args, topology):
    print("passa ")
    k_shortest_paths = {}
    
    for idn1, n1 in enumerate(topology.graph['source_nodes']):
        for idn2, n2 in enumerate(topology.graph['dcs']):
            print("chama === ",args.k_paths)
            paths = get_k_safest_paths(topology, n1, n2, args.k_paths)
            print("retorna s_safest")
            lengths = [get_path_weight(topology, path, 'link_failure_probability') for path in paths]
            objs = []
            for path, length in zip(paths, lengths):
                objs.append(Path(path, length))
            # both directions have the same paths, i.e., bidirectional symmetrical links
            k_shortest_paths[n1, n2] = objs
            k_shortest_paths[n2, n1] = objs
    topology.graph['prob_ksp'] = k_shortest_paths
    return topology

def set_failure_probabilities(args,topology):
    tf: str = args.topology_file
    tfpath = "config/topologies/"+tf
    elementTree = ET.parse(tfpath)
    root = elementTree.getroot()

    for zone in root.findall(".//zone"):
        for region in root.findall(".//zone[@id='"+zone.attrib['id']+"']/region"):
            for link in root.findall(".//zone[@id='"+zone.attrib['id']+"']/region[@id='"+region.attrib['id']+"']/disaster_link"):
                for src in root.findall(".//link[@id='"+link.text+"']/source"):
                    link_src = src.text
                for tgt in root.findall(".//link[@id='"+link.text+"']/target"):
                    link_tgt = tgt.text
                topology[link_src][link_tgt]['link_failure_probability'] = float(link.attrib['probability'])
    return topology