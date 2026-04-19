import sys
import traceback

print("Starting wrapped main...", flush=True)
try:
    print("Importing main...", flush=True)
    import main
    print("Importing QApplication...", flush=True)
    from PyQt5.QtWidgets import QApplication
    print("Importing MainWindow...", flush=True)
    from MainWindow import MainWindow

    print("Creating app...", flush=True)
    app = QApplication(sys.argv)
    
    print("Creating MainWindow...", flush=True)
    main_window = MainWindow()
    
    print("Showing main window...", flush=True)
    main_window.show()
    
    print("Executing app...", flush=True)
    sys.exit(app.exec_())
except Exception as e:
    print("Caught Exception:", type(e), flush=True)
    traceback.print_exc()
except SystemExit as e:
    print("Caught SystemExit with code:", e.code, flush=True)
finally:
    print("End of test_imports.py", flush=True)
