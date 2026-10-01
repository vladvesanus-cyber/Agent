"""
Допоміжні функції для всієї системи
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List
import numpy as np
from datetime import datetime


# ===== КОНФІГУРАЦІЯ =====

def load_config(config_file: str) -> Dict:
    """
    Завантажити конфіг з YAML файлу
    
    Args:
        config_file: Шлях до YAML файлу
    
    Returns:
        Словник конфігурації
    
    Example:
        config = load_config('config/environment.yaml')
    """
    
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Конфіг не знайдено: {config_file}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            raise ValueError(f"Конфіг пустий: {config_file}")
        
        return config
    
    except yaml.YAMLError as e:
        raise ValueError(f"Помилка парсингу YAML: {e}")
    
    except Exception as e:
        raise Exception(f"Помилка завантаження конфіга: {e}")


def save_config(config: Dict, output_file: str):
    """
    Зберегти конфіг в YAML файл
    
    Args:
        config: Словник конфігурації
        output_file: Шлях для збереження
    """
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Конфіг збережено: {output_file}")
    
    except Exception as e:
        print(f"❌ Помилка збереження конфіга: {e}")


# ===== ДИРЕКТОРІЇ =====

def ensure_dir(directory: str) -> Path:
    """
    Переконатись що директорія існує, створити якщо потрібно
    
    Args:
        directory: Шлях до директорії
    
    Returns:
        Path об'єкт директорії
    
    Example:
        results_dir = ensure_dir('results')
    """
    
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    return dir_path


def ensure_file_dir(file_path: str):
    """
    Переконатись що директорія для файлу існує
    
    Args:
        file_path: Шлях до файлу
    """
    
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)


# ===== ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ =====

def save_results(results: Dict, output_file: str, format: str = 'json'):
    """
    Зберегти результати в JSON або YAML
    
    Args:
        results: Словник результатів
        output_file: Шлях для збереження
        format: 'json' або 'yaml'
    """
    
    ensure_file_dir(output_file)
    
    try:
        if format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        elif format == 'yaml':
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(results, f, default_flow_style=False, allow_unicode=True)
        
        else:
            raise ValueError(f"Невідомий формат: {format}")
        
        print(f"✅ Результати збережено: {output_file}")
    
    except Exception as e:
        print(f"❌ Помилка збереження результатів: {e}")


def load_results(input_file: str) -> Dict:
    """
    Завантажити результати з JSON або YAML
    
    Args:
        input_file: Шлях до файлу
    
    Returns:
        Словник результатів
    """
    
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Файл не знайдено: {input_file}")
    
    try:
        if input_file.endswith('.json'):
            with open(input_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif input_file.endswith('.yaml') or input_file.endswith('.yml'):
            with open(input_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        else:
            raise ValueError(f"Невідомий формат файлу: {input_file}")
    
    except Exception as e:
        raise Exception(f"Помилка завантаження результатів: {e}")


# ===== ДИСТАНЦІЯ =====

def manhattan_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Манхеттенська дистанція (городська блокова дистанція)
    
    Args:
        p1: (x1, y1)
        p2: (x2, y2)
    
    Returns:
        Дистанція
    
    Example:
        dist = manhattan_distance((0, 0), (3, 4))  # = 7
    """
    
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Евклідова дистанція (прямолінійна)
    
    Args:
        p1: (x1, y1)
        p2: (x2, y2)
    
    Returns:
        Дистанція
    
    Example:
        dist = euclidean_distance((0, 0), (3, 4))  # = 5.0
    """
    
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def chebyshev_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Дистанція Чебишева (максимум компонент)
    
    Args:
        p1: (x1, y1)
        p2: (x2, y2)
    
    Returns:
        Дистанція
    
    Example:
        dist = chebyshev_distance((0, 0), (3, 4))  # = 4
    """
    
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


# ===== МАТЕМАТИКА =====

def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Обмежити значення в діапазоні
    
    Args:
        value: Значення
        min_val: Мінімум
        max_val: Максимум
    
    Returns:
        Обмежене значення
    
    Example:
        x = clamp(150, 0, 100)  # = 100
    """
    
    return max(min_val, min(value, max_val))


def normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Нормалізувати значення в діапазон [0, 1]
    
    Args:
        value: Значення
        min_val: Мінімум вихідного діапазону
        max_val: Максимум вихідного діапазону
    
    Returns:
        Нормалізоване значення (0-1)
    
    Example:
        norm = normalize(75, 0, 100)  # = 0.75
    """
    
    if max_val == min_val:
        return 0.0
    
    return (value - min_val) / (max_val - min_val)


def lerp(a: float, b: float, t: float) -> float:
    """
    Лінійна інтерполяція
    
    Args:
        a: Стартове значення
        b: Кінцеве значення
        t: Параметр (0-1)
    
    Returns:
        Інтерпольоване значення
    
    Example:
        val = lerp(0, 100, 0.5)  # = 50.0
    """
    
    return a + (b - a) * t


# ===== ФОРМАТ =====

def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Форматувати значення як відсоток
    
    Args:
        value: Значення (0-1 або 0-100)
        decimals: Кількість знаків після коми
    
    Returns:
        Форматований рядок
    
    Example:
        s = format_percentage(0.85, 1)  # = "85.0%"
    """
    
    if value <= 1:
        value = value * 100
    
    return f"{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """
    Форматувати число з фіксованою кількістю знаків
    
    Args:
        value: Число
        decimals: Кількість знаків після коми
    
    Returns:
        Форматований рядок
    """
    
    return f"{value:.{decimals}f}"


def get_timestamp() -> str:
    """
    Отримати поточний час у форматі ISO
    
    Returns:
        Часова мітка
    
    Example:
        ts = get_timestamp()  # "2024-01-15T10:30:45.123456"
    """
    
    return datetime.now().isoformat()


def get_timestamp_filename() -> str:
    """
    Отримати часову мітку для використання в назвах файлів
    
    Returns:
        Часова мітка
    
    Example:
        name = get_timestamp_filename()  # "20240115_103045"
    """
    
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ===== СПИСКИ =====

def flatten_list(nested_list: List) -> List:
    """
    Розгорнути вкладений список
    
    Args:
        nested_list: Вкладений список
    
    Returns:
        Розгорнутий список
    
    Example:
        flat = flatten_list([[1, 2], [3, [4, 5]]])  # [1, 2, 3, 4, 5]
    """
    
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def dict_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    Об'єднати два словники (dict2 перевизначає dict1)
    
    Args:
        dict1: Перший словник
        dict2: Другий словник (має приорітет)
    
    Returns:
        Об'єднаний словник
    """
    
    result = dict1.copy()
    result.update(dict2)
    return result


# ===== ЛОГУВАННЯ =====

def print_section(title: str, width: int = 70):
    """
    Вивести розділ з заголовком
    
    Args:
        title: Заголовок
        width: Ширина лінії
    """
    
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}\n")


def print_subsection(title: str, width: int = 70):
    """
    Вивести підрозділ з заголовком
    
    Args:
        title: Заголовок
        width: Ширина лінії
    """
    
    print(f"\n{'-'*width}")
    print(f"  {title}")
    print(f"{'-'*width}\n")


def print_progress(current: int, total: int, prefix: str = '', width: int = 30):
    """
    Вивести прогрес-бар
    
    Args:
        current: Поточний крок
        total: Всього кроків
        prefix: Префікс перед баром
        width: Ширина бара
    
    Example:
        print_progress(5, 10, "Processing")
    """
    
    if total == 0:
        return
    
    percent = current / total
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    
    print(f"\r{prefix} [{bar}] {percent*100:.1f}% ({current}/{total})", end='')
    
    if current == total:
        print()  # Нова лінія в кінці


# ===== ВАЛІДАЦІЯ =====

def validate_config(config: Dict, required_keys: List[str]) -> bool:
    """
    Перевірити чи конфіг має всі необхідні ключі
    
    Args:
        config: Конфіг для перевірки
        required_keys: Список необхідних ключів
    
    Returns:
        True якщо валіден, інакше False
    """
    
    for key in required_keys:
        if key not in config:
            print(f"❌ Недостає ключа в конфігу: {key}")
            return False
    
    return True


def validate_value(value: Any, expected_type: type, 
                  min_val: Any = None, max_val: Any = None) -> bool:
    """
    Перевірити значення
    
    Args:
        value: Значення для перевірки
        expected_type: Очікуваний тип
        min_val: Мінімум (опціонально)
        max_val: Максимум (опціонально)
    
    Returns:
        True якщо валідне, інакше False
    """
    
    if not isinstance(value, expected_type):
        print(f"❌ Невірний тип: очікувалось {expected_type}, отримано {type(value)}")
        return False
    
    if min_val is not None and value < min_val:
        print(f"❌ Значення менше мінімуму: {value} < {min_val}")
        return False
    
    if max_val is not None and value > max_val:
        print(f"❌ Значення більше максимуму: {value} > {max_val}")
        return False
    
    return True