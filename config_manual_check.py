from quantedge.shared.config import settings

print("Application:", settings.app_name)
print("Environment:", settings.app_env.value)
print("Debug:", settings.debug)