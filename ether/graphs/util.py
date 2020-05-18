import datetime

import ether.graphs.api.cloudping as cloudping
import ether.graphs.api.gcloudping as gcloudping
import ether.graphs.api.wondernetwork as wondernetwork
import ether.graphs.network as network


def fetch_and_save_all_graphs(folder: str = 'graphs') -> None:
    print('Fetch cloudping graph')
    cloudping_graph = network.create_latency_network_graph(cloudping.get_average(days=7))

    print('Fetch gcloudping graph')
    gcloudping_graph = network.create_latency_network_graph(gcloudping.get_matrix())

    print('Fetch wondernetwork graph')
    wondernetwork_graph = network.create_latency_network_graph(wondernetwork.get_matrix())

    today = datetime.datetime.now().strftime("%Y_%m_%d")
    for graph, name in [(cloudping_graph, 'cloudping'), (gcloudping_graph, 'gcloudping'),
                        (wondernetwork_graph, 'wondernetwork')]:
        print(f'Save {name} graph under: {folder}/{name}_latest.graphml')
        network.save_network_graph(graph, f'{folder}/{name}_latest.graphml')
        network.save_network_graph(graph, f'{folder}/{name}_{today}.graphml')


def read_latest_graph(api: str, folder='graphs'):
    """
    param api: currently supported 'cloudping', 'gcloudping', 'wondernetwork'
    raises FileNotFoundError
    """
    file = f'{folder}/{api}_latest.graphml'
    print(f'Read latest graph of {api}, from: {file}')
    return network.read_network_graph(file)
