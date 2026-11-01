import unittest
from skelion_agent.priority_queue import PriorityQueue


class TestPriorityQueue(unittest.TestCase):
    def test_priority_order(self):
        pq = PriorityQueue()
        pq.push("low", priority=10)
        pq.push("high", priority=1)
        self.assertEqual(pq.pop(), "high")
        self.assertEqual(pq.pop(), "low")

    def test_clean_text(self):
        pq = PriorityQueue()
        res = pq.clean_text("Hello World!..")
        self.assertEqual(res, "hello world")


if __name__ == "__main__":
    unittest.main()
