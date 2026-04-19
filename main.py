import sys
# import qdarkstyle
from PyQt5.QtWidgets import QApplication
from MainWindow import MainWindow


def main():
    import os
    for d in ['car_images', 'license_images', 'reported_car', 'tickets']:
        os.makedirs(d, exist_ok=True)
    app = QApplication(sys.argv)
    main_window = MainWindow()
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
