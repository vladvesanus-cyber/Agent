"""
Reproducibility - просто встановити seed
"""

import numpy as np
import random
import os


def set_seed(seed: int):
    """
    Встановити seed для відтворюваності
    
    Args:
        seed: Seed число (e.g., 42)
    """
    
    # NumPy random
    np.random.seed(seed)
    
    # Python random
    random.seed(seed)
    
    # Python hash'и
    os.environ['PYTHONHASHSEED'] = str(seed)
    
    print(f"✅ Seed встановлено: {seed}")


def verify_reproducibility(result1: dict, result2: dict) -> bool:
    """
    Перевірити чи результати однакові
    """
    
    return (
        abs(result1['exploration_ratio'] - result2['exploration_ratio']) < 0.001 and
        result1['total_steps'] == result2['total_steps']
    )