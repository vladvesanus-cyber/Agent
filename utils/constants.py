"""
Глобальні константи для всієї системи
"""

# ===== ДРОН =====

NUM_MOTORS = 4
NUM_SENSORS = 3
NUM_PROPELLERS = 4

BATTERY_CAPACITY = 100  # % енергії (за замовчуванням)
MAX_ALTITUDE = 20  # метри

MOTOR_MAX_RPM = 8000
MOTOR_MAX_TEMPERATURE = 85  # °C

BATTERY_MAX_TEMPERATURE = 50  # °C
BATTERY_CRITICAL_TEMPERATURE = 45  # °C

# ===== ФІЗИКА =====

ENERGY_BASE_COST = 1.0  # % енергії за крок на землі
ENERGY_ALTITUDE_MULTIPLIER = True  # Енергія зростає з висотою

SENSOR_ACCURACY_BASE = 100  # % точності на землі
SENSOR_ACCURACY_DECLINE_RATE = 2  # (altitude^1.5) * RATE

# ===== КОЛІЗІЯ =====

COLLISION_DETECTION_ENABLED = True

# Пошкодження за типом терену
DAMAGE_MAP = {
    'hard_obstacle': 1.0,      # 100% пошкодження (стіна)
    'tree_branches': 0.3,      # 30% пошкодження (гілки)
    'mountain': 0.5,           # 50% пошкодження (гора)
    'water': 0.8,              # 80% пошкодження (вода)
    'out_of_bounds': 1.0,      # 100% пошкодження
    'free': 0.0                # 0% пошкодження
}

# ===== КАРТА =====

MAP_WIDTH_SMALL = 20
MAP_HEIGHT_SMALL = 20

MAP_WIDTH_MEDIUM = 30
MAP_HEIGHT_MEDIUM = 30

MAP_WIDTH_LARGE = 50
MAP_HEIGHT_LARGE = 50

# Терен ратіо (відсоток від карти)
TERRAIN_OBSTACLE_EASY = 0.15
TERRAIN_OBSTACLE_MEDIUM = 0.25
TERRAIN_OBSTACLE_HARD = 0.35

TERRAIN_TREE_RATIO = 0.05
TERRAIN_WATER_RATIO = 0.03
TERRAIN_MOUNTAIN_RATIO = 0.02

# ===== КОНФІГУРАЦІЯ =====

DEFAULT_SEED = 42
MAX_STEPS = 1000
OBSERVATION_RADIUS = 2  # 5x5 видимість

# ===== МЕТРИКИ =====

EXPLORATION_SUCCESS_THRESHOLD = 0.80  # 80% дослідження = успіх

# Performance Measure коефіцієнти
PERFORMANCE_EXPLORATION_WEIGHT = 1000
PERFORMANCE_RETURN_BONUS = 100
PERFORMANCE_ENERGY_PENALTY = 2
PERFORMANCE_TIME_PENALTY = 0.1

# ===== SIMULATION =====

NUM_RUNS_PER_CONFIG = 20
NUM_CONFIGURATIONS = 3

# ===== БАТАРЕЯ ДЕГРАДАЦІЯ =====

BATTERY_DEGRADATION_PER_CYCLE = 0.5  # % здоров'я за цикл
BATTERY_THERMAL_DEGRADATION_RATE = 0.1  # % за °C вище 25

# ===== МОТОР =====

MOTOR_WEAR_RATE = 0.5  # % зносу за стрес
MOTOR_EFFICIENCY_DECLINE_RATE = 1.0  # % за % зносу

# ===== ДАТЧИК =====

SENSOR_DIRT_RATE_ALTITUDE = 0.1  # % забруднення за крок на низькій висоті
SENSOR_DIRT_RATE_COLLISION = {
    'camera': 20,     # % за колізію
    'lidar': 10,
    'ultrasonic': 5
}

SENSOR_ACCURACY_CALIBRATION_DECLINE = 0.01  # % за крок

# ===== СТРУКТУРА =====

STRUCTURE_INTEGRITY_CRITICAL = 50  # % мінімум для польоту
PROPELLER_HEALTH_MINIMUM = 30  # % мінімум на пропелер

# ===== ЗДОРОВ'Я =====

HEALTH_CRITICAL_THRESHOLD = 40  # % мінімум
HEALTH_WARNING_THRESHOLD = 60   # % попередження

# ===== ВІЗУАЛІЗАЦІЯ =====

ANIMATION_FRAME_DELAY = 0.01  # секунд
ANIMATION_TRAIL_LENGTH = 50  # кроків для траєкторії

# ===== ФАЙЛИ =====

CONFIG_DIR = 'config'
RESULTS_DIR = 'results'
LOGS_DIR = 'logs'
DATA_DIR = 'data'

# ===== ВЕРСІЇ =====

SYSTEM_VERSION = '1.0.0'
PYTHON_MIN_VERSION = '3.8'

# ===== ПОМИЛКИ =====

DEFAULT_RANDOM_SEED = 42
MAX_RETRIES = 3

# ===== TEMPERATURE =====

AMBIENT_TEMPERATURE = 25  # °C
TEMPERATURE_COOLING_RATE = 0.05

# ===== ALTITUDE EFFECTS =====

ALTITUDE_ENERGY_MULTIPLIER_BASE = 1.0
ALTITUDE_COOLING_FACTOR = 1.3  # На висоті охолоджується погано