import sys
from PyQt5.QtWidgets import QApplication
from ui.dashboard import DroneDashboard

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = DroneDashboard()
    dashboard.show()
    sys.exit(app.exec_()) 