import sys

print("Python module search path:")
for path in sys.path:
    print(path)

from modules import add, multiply

print("Addition:", add(10, 20))
print("Multiplication:", multiply(10, 20))


from modules.calculator import add, multiply

print("Addition:", add(10, 20))
print("Multiplication:", multiply(10, 20))