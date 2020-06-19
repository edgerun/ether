import datetime

import networkx as nx

import ether.inet.graph as network
from ether.inet.fetch import sources
from ether.inet.graph import add_to_graph


def fetch_and_save_all_graphs(folder: str = 'inet') -> None:
    today = datetime.datetime.now().strftime("%Y_%m_%d")

    for name, source in sources.items():
        graph = nx.DiGraph()
        print('fetching from', name)
        add_to_graph(graph, source.fetch())

        network.save_network_graph(graph, f'{name}_{today}.graphml')


def read_latest_graph(api: str, folder='inet'):
    """
    param api: currently supported 'cloudping', 'gcloudping', 'wondernetwork'
    raises FileNotFoundError
    """
    file = f'{folder}/{api}_latest.graphml'
    print(f'Read latest graph of {api}, from: {file}')
    return network.read_network_graph(file)
