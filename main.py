import sys
from PySide6 import QtWidgets, QtCore

from lib import ui as ui_lib

def main():
    app = QtWidgets.QApplication([])
    app.setOverrideCursor(QtCore.Qt.BlankCursor)

    ui = ui_lib.SportsStatusUI(debug=False)
    ui.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()