import yaml
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List
import numpy as np
from datetime import datetime


# configuration

def load_config(config_file: str) -> Dict:
    
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_file}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            raise ValueError(f"Config is empty: {config_file}")
        
        return config
    
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML: {e}")
    
    except Exception as e:
        raise Exception(f"Error loading config: {e}")


def save_config(config: Dict, output_file: str):
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Config saved: {output_file}")
    
    except Exception as e:
        print(f"❌ Error saving config: {e}")


def ensure_dir(directory: str) -> Path:
    
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    return dir_path


def ensure_file_dir(file_path: str):
    
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)


# ===== ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ =====

def make_json_safe(obj: Any) -> Any:

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return sorted(make_json_safe(v) for v in obj)
    if isinstance(obj, np.generic):  # np.float64, np.int64, np.bool_, ...
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def save_results(results: Dict, output_file: str, format: str = 'json'):
    
    ensure_file_dir(output_file)

    safe_results = make_json_safe(results)

    try:
        if format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(safe_results, f, indent=2, ensure_ascii=False)

        elif format == 'yaml':
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(safe_results, f, default_flow_style=False, allow_unicode=True)
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    except Exception as e:
        print(f"❌ Error saving results: {e}")


def load_results(input_file: str) -> Dict:
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")
    
    try:
        if input_file.endswith('.json'):
            with open(input_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif input_file.endswith('.yaml') or input_file.endswith('.yml'):
            with open(input_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        else:
            raise ValueError(f"Unknown file format: {input_file}")
    
    except Exception as e:
        raise Exception(f"Error loading results: {e}")


#distance

def manhattan_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def chebyshev_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))


def normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 0.0
    
    return (value - min_val) / (max_val - min_val)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ===== ФОРМАТ =====

def format_percentage(value: float, decimals: int = 1) -> str:
    if value <= 1:
        value = value * 100
    
    return f"{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def get_timestamp() -> str:
    return datetime.now().isoformat()


def get_timestamp_filename() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ===== СПИСКИ =====

def flatten_list(nested_list: List) -> List:
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def dict_merge(dict1: Dict, dict2: Dict) -> Dict:    
    result = dict1.copy()
    result.update(dict2)
    return result


# ===== ЛОГУВАННЯ =====

def print_section(title: str, width: int = 70):
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}\n")


def print_subsection(title: str, width: int = 70):
    print(f"\n{'-'*width}")
    print(f"  {title}")
    print(f"{'-'*width}\n")


def print_progress(current: int, total: int, prefix: str = '', width: int = 30):
    if total == 0:
        return
    
    percent = current / total
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    
    print(f"\r{prefix} [{bar}] {percent*100:.1f}% ({current}/{total})", end='')
    
    if current == total:
        print()  


# ===== ВАЛІДАЦІЯ =====

def validate_config(config: Dict, required_keys: List[str]) -> bool:
    
    for key in required_keys:
        if key not in config:
            print(f"❌ Missing key in config: {key}")
            return False
    
    return True


def validate_value(value: Any, expected_type: type, 
                  min_val: Any = None, max_val: Any = None) -> bool:
    
    if not isinstance(value, expected_type):
        print(f"❌ Invalid type: expected {expected_type}, got {type(value)}")
        return False
    
    if min_val is not None and value < min_val:
        print(f"❌ Value is below minimum: {value} < {min_val}")
        return False
    
    if max_val is not None and value > max_val:
        print(f"❌ Value is above maximum: {value} > {max_val}")
        return False
    
    return True