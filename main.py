from PySide6.QtWidgets import  QApplication
from main_window import AuthWindow

app = QApplication([])
window = AuthWindow()
window.show()
app.exec()