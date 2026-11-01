import pytest
import random
from skelion_agent.quantizer import SlidingWindowVectorQuantizer


def test_quantizer_initialization():
    quantizer = SlidingWindowVectorQuantizer(dimension=16, num_centroids=10, window_size=100)
    assert quantizer.get_codebook_size() == 10
    assert quantizer.get_window_size() == 0


def test_quantizer_add_and_compression():
    quantizer = SlidingWindowVectorQuantizer(dimension=8, num_centroids=4, window_size=50)
    vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    
    idx, error = quantizer.add_vector(vector)
    assert 0 <= idx < 4
    assert error >= 0.0
    assert quantizer.get_window_size() == 1


def test_quantizer_dimension_mismatch():
    quantizer = SlidingWindowVectorQuantizer(dimension=4, num_centroids=2, window_size=10)
    with pytest.raises(ValueError):
        quantizer.add_vector([1.0, 2.0, 3.0, 4.0, 5.0])


def test_sliding_window_bound():
    window_limit = 20
    quantizer = SlidingWindowVectorQuantizer(dimension=4, num_centroids=2, window_size=window_limit)
    
    for i in range(35):
        vec = [float(i), float(i+1), float(i+2), float(i+3)]
        quantizer.add_vector(vec)
        
    assert quantizer.get_window_size() == window_limit
