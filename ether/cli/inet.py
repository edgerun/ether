from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime

import networkx as nx

from ether.inet.fetch import sources
from ether.inet.graph import add_to_graph, save_network_graph


def fetch_and_save(name, source):
    today = datetime.now().strftime("%Y_%m_%d")
    graph = nx.DiGraph()
    print('fetching from', name)
    add_to_graph(graph, source.fetch())

    filename = f'{name}_{today}.graphml'
    save_network_graph(graph, filename)
    print('saved', filename)


def main():
    with ThreadPoolExecutor(4) as pool:
        futures = list()

        for name, source in sources.items():
            ftr = pool.submit(fetch_and_save, name, source)
            futures.append(ftr)

        for ftr in futures:
            ftr.result()


if __name__ == '__main__':
    main()
