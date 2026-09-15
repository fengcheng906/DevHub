# Python 环境验收测试脚本
# 用途：验证 Python 是否正常工作（第 2 周任务 1 的验收）
# 运行方法：python test_python.py

import sys
import datetime

print("=== Python 环境测试 ===")
print("Python 版本:", sys.version.split()[0])
print("当前时间:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# 简单计算测试
result = 2 ** 10
print("计算测试: 2 的 10 次方 =", result)

if result == 1024:
    print("结论: Python 环境完全正常，可以开始学习！")
else:
    print("警告: 计算结果异常，需要检查环境")
