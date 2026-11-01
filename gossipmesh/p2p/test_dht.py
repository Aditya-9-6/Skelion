import unittest
from gossipmesh.p2p.dht import KademliaDHT, calculate_xor_distance
from gossipmesh.p2p.node import P2PNode


class TestKademliaDHT(unittest.TestCase):
    def test_xor_distance(self):
        id1 = "0000000000000000000000000000000000000000000000000000000000000001"
        id2 = "0000000000000000000000000000000000000000000000000000000000000003"
        dist = calculate_xor_distance(id1, id2)
        self.assertEqual(dist, 2)

    def test_dht_add_and_find(self):
        dht = KademliaDHT(node_id="0000000000000000000000000000000000000000000000000000000000000000", k=2)
        added1 = dht.add_peer("0000000000000000000000000000000000000000000000000000000000000001", "127.0.0.1:8001")
        added2 = dht.add_peer("0000000000000000000000000000000000000000000000000000000000000002", "127.0.0.1:8002")
        added3 = dht.add_peer("0000000000000000000000000000000000000000000000000000000000000003", "127.0.0.1:8003")

        self.assertTrue(added1)
        self.assertTrue(added2)
        # Should reject because k=2 bucket capacity reached
        self.assertFalse(added3)

        close_nodes = dht.find_close_nodes("0000000000000000000000000000000000000000000000000000000000000001", count=1)
        self.assertEqual(len(close_nodes), 1)
        self.assertEqual(close_nodes[0][0], "0000000000000000000000000000000000000000000000000000000000000001")

    def test_p2p_node_integration(self):
        node = P2PNode(node_id="node_test_id")
        node.register_peer("peer_1", "192.168.1.10:9000")
        closest = node.get_closest_peers("target_id", count=5)
        self.assertEqual(len(closest), 1)
        self.assertEqual(closest[0]["peer_id"], "peer_1")
        node.unregister_peer("peer_1")
        self.assertEqual(len(node.get_closest_peers("target_id")), 0)


if __name__ == "__main__":
    unittest.main()
