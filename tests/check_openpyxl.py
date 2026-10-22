try:
    import openpyxl
    print("openpyxl is installed:", openpyxl.__version__)
except ImportError:
    print("openpyxl is NOT installed")
