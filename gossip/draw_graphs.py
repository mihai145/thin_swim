import networkx as nx
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# sns.set_theme()


def draw_complete_graph():
    for i in range(5, 10 + 1):
        K = nx.complete_graph(i)
        nx.draw_networkx(K, with_labels=True)
        plt.savefig(f"K_{i}.pdf", format="pdf")
        plt.clf()


def draw_ring_graph():
    for i in range(5, 10 + 1):
        K = nx.cycle_graph(i)
        nx.draw_networkx(K, with_labels=True)
        plt.savefig(f"ring_{i}.pdf", format="pdf")
        plt.clf()


def draw_random_geometric_graph(run):
    # find a good geometric graph for display

    n = 12
    while True:
        K = nx.random_geometric_graph(n, radius=0.8, dim=3)
        edges = K.edges()
        node_positions = nx.get_node_attributes(K, "pos")

        # existance of a node with degree == 2 and with close neighbors
        chosen = -1
        for i in range(n):
            deg, max_dist_to_neighbor = 0, 0
            for edge in K.edges():
                if edge[0] == i or edge[1] == i:
                    deg += 1
                    max_dist_to_neighbor = max(
                        max_dist_to_neighbor,
                        (node_positions[edge[0]][0] - node_positions[edge[1]][0]) ** 2
                        + (node_positions[edge[0]][1] - node_positions[edge[1]][1]) ** 2
                        + (node_positions[edge[0]][2] - node_positions[edge[1]][2])
                        ** 2,
                    )

            if deg <= 4 and max_dist_to_neighbor <= 0.23**2:
                chosen = i
                break

        # the graph must be connected, have few edges and a node as defined above
        if nx.is_connected(K) and len(K.edges) <= n * 2 and chosen != -1:
            break

    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")

    for i in range(n):
        color = "red" if i != chosen else "yellow"
        ax.scatter(
            node_positions[i][0],
            node_positions[i][1],
            node_positions[i][2],
            marker="o",
            color=color,
        )

    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x = node_positions[chosen][0] + 0.25 * np.outer(np.cos(u), np.sin(v))
    y = node_positions[chosen][1] + 0.25 * np.outer(np.sin(u), np.sin(v))
    z = node_positions[chosen][2] + 0.25 * np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x, y, z, color="lightblue", alpha=0.3)

    for edge in edges:
        p1, p2 = node_positions[edge[0]], node_positions[edge[1]]
        ax.plot(
            [p1[0], p2[0]],
            [p1[1], p2[1]],
            [p1[2], p2[2]],
            color="lightgreen",
            alpha=0.8,
        )

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    plt.savefig(f"random_geometric_graph_{run}.pdf", format="pdf")
    plt.clf()
    print(f"Done run {run}")


if __name__ == "__main__":
    # draw_complete_graph()
    # draw_ring_graph()

    # try a few such graphs, until one proper for presentation is found
    # for i in range(50):
    #     draw_random_geometric_graph(i)
    pass
