import sys
from PySide6 import QtWidgets

from lib import ui as ui_lib

def main():
    app = QtWidgets.QApplication([])

    ui = ui_lib.SportsStatusUI()
    ui.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()