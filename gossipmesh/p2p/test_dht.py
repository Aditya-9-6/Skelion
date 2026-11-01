import unittest
from gossipmesh.p2p.dht import KademliaDHT, calculate_distance, generate_node_id
from gossipmesh.p2p.node import PeerManager


class TestKademliaDHT(unittest.TestCase):
    def test_distance_calculation(self):
        id1 = generate_node_id("nodeA")
        id2 = generate_node_id("nodeB")
        dist = calculate_distance(id1, id2)
        self.assertGreater(dist, 0)
        self.assertEqual(calculate_distance(id1, id1), 0)

    def test_dht_routing_and_buckets(self):
        local_id = generate_node_id("local")
        dht = KademliaDHT(local_node_id=local_id, k_size=5)
        
        peer_ids = [generate_node_id(f"peer_{i}") for i in range(10)]
        for i, pid in enumerate(peer_ids):
            added = dht.add_node(pid, f"127.0.0.1:{8000 + i}")
            self.assertTrue(added)
            
        closest = dht.find_closest_nodes(local_id, count=3)
        self.assertEqual(len(closest), 3)

    def test_peer_manager_dht_integration(self):
        local_id = generate_node_id("manager_local")
        manager = PeerManager(local_peer_id=local_id)
        
        p_id = generate_node_id("remote_peer")
        manager.add_peer(p_id, "127.0.0.1:9000")
        
        self.assertIsNotNone(manager.get_peer(p_id))
        closest = manager.find_closest_peers(local_id, count=5)
        self.assertTrue(any(pid == p_id for pid, _ in closest))
        
        manager.remove_peer(p_id)
        self.assertIsNone(manager.get_peer(p_id))


if __name__ == "__main主要的__":
    unittest.main()
