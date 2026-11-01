import unittest
from gossipmesh.p2p.dht import KademliaNode, KademliaDHT
from gossipmesh.p2p.node import P2PNode


class TestKademliaDHT(unittest.TestCase):
    def test_xor_distance(self):
        node1 = KademliaNode("node_a", "127.0.0.1:8000")
        node2 = KademliaNode("node_b", "127.0.0.1:8001")
        dist = node1.xor_distance(node2.digest)
        self.assertGreater(dist, 0)
        self.assertEqual(node1.xor_distance(node1.digest), 0)

    def test_dht_routing_and_lookup(self):
        dht = KademliaDHT("local_node", "127.0.0.1:9000")
        dht.add_node("peer_1", "127.0.0.1:9001")
        dht.add_node("peer_2", "127.0.0.1:9002")
        dht.add_node("peer_3", "127.0.0.1:9003")

        closest = dht.find_closest_nodes("target_peer", count=2)
        self.assertEqual(len(closest), 2)

        dht.remove_node("peer_1")
        closest_after_remove = dht.find_closest_nodes("target_peer", count=5)
        peer_ids = [n.peer_id for n in closest_after_remove]
        self.assertNotIn("peer_1", peer_ids)
        self.assertIn("peer_2", peer_ids)

    def test_p2p_node_integration(self):
        p2p_node = P2PNode("node_main", "127.0.0.1:7000")
        p2p_node.register_peer("node_alpha", "127.0.0.1:7001")
        p2p_node.register_peer("node_beta", "127.0.0.1:7002")

        status = p2p_node.get_status()
        self.assertEqual(status["known_dht_peers"], 2)

        closest = p2p_node.find_peers("node_target", count=1)
        self.assertEqual(len(closest), 1)

        p2p_node.unregister_peer("node_alpha")
        status_updated = p2p_node.get_status()
        self.assertEqual(status_updated["known_dht_peers"], 1)


if __name__ == "__main__":
    unittest.main()
