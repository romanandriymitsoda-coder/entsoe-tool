import pkgutil
m = pkgutil.find_loader("pip_system_certs")
print("pip_system_certs:", "installed" if m else "not installed")
