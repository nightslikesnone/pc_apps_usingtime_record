# config.py
# 存放所有可调整的配置参数

IDLE_THRESHOLD = 30        # 空闲阈值，单位秒
CHECK_INTERVAL = 1          # 监控循环间隔，秒
DB_PATH = 'usage.db'        # 数据库文件路径

# 番茄钟配置
TOMATO_WORK_MINUTES = 25             # 工作时长（分钟）
TOMATO_SHORT_BREAK_MINUTES = 5       # 短休息时长（分钟）
TOMATO_LONG_BREAK_MINUTES = 15       # 长休息时长（分钟）
TOMATO_CYCLES_BEFORE_LONG_BREAK = 4  # 几个工作周期后休息长一点