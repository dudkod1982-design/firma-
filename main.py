import sys
from PySide6.QtWidgets import QApplication
from app.mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Firma — Salvagnini P4 Programmer")
    app.setOrganizationName("firma")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
