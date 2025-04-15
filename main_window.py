import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QMessageBox, 
    QTabWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, QDialog, QFormLayout, QComboBox, 
    QSpinBox, QFileDialog, QMenu, QTabBar, QDateEdit
)
from PySide6.QtCore import Qt, QDate, QSize, QEvent, QPoint, QRegularExpression, QLocale
from PySide6.QtGui import QIcon, QPixmap, QAction, QIntValidator, QRegularExpressionValidator
import hashlib
from datetime import datetime
from models import (
    Postavshik, TipPostavshika, Tovar, TipTovara, Sotrudnik, Pol, 
    OtchetyPoPostuplenijuTovarov, OtchetyPoOstatkamTovarov, OtchetyPoUbytomuTovaru, Gorod, Ulica, DomStroenie, Connect
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Пользователи и их хэшированные пароли
USERS = {
    "direktor": hashlib.sha256("123456".encode()).hexdigest(),
    "florist": hashlib.sha256("123456".encode()).hexdigest()
}

class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reports_menu = None
        self.reports_index = -1

    def set_reports_menu(self, menu, index):
        self.reports_menu = menu
        self.reports_index = index

    def enterEvent(self, event):
        if self.reports_menu and self.reports_index >= 0:
            tab_rect = self.tabRect(self.reports_index)
            if tab_rect.contains(self.mapFromGlobal(QPoint(event.globalPosition().x(), event.globalPosition().y()))):
                menu_pos = self.mapToGlobal(tab_rect.bottomLeft())
                self.reports_menu.exec_(menu_pos)
        super().enterEvent(event)

class ResizableSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)  # Отступы внутри панели
        self.setFixedWidth(300)  # Начальная ширина панели
        self.min_width = 200  # Минимальная ширина
        self.max_width = 500  # Максимальная ширина
        self.resize_edge = 10  # Ширина области для захвата (левый край)
        self.is_resizing = False
        self.start_x = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos().x() <= self.resize_edge:
                self.is_resizing = True
                self.start_x = event.globalX()
                self.setCursor(Qt.SizeHorCursor)
                print("Начало изменения размера панели...")

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            delta_x = self.start_x - event.globalX()
            new_width = self.width() + delta_x
            new_width = max(self.min_width, min(self.max_width, new_width))
            self.setFixedWidth(new_width)
            self.start_x = event.globalX()
            print(f"Новая ширина панели: {new_width} пикселей")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_resizing:
            self.is_resizing = False
            self.unsetCursor()
            print("Изменение размера панели завершено.")

class SupplierForm(QWidget):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.setObjectName("formWidget")
        self.supplier = supplier

        layout = QFormLayout()
        layout.setSpacing(10)

        self.title_label = QLabel("Поставщик" if supplier else "Добавить поставщика")
        self.title_label.setObjectName("titleLabel")
        layout.addRow(self.title_label)

        self.name_input = QLineEdit()
        self.name_input.setText(supplier.nazvanie_postavshika if supplier else "")
        self.name_input.setPlaceholderText("Введите название поставщика")
        layout.addRow("Название поставщика:", self.name_input)

        self.type_input = QComboBox()
        self.type_input.addItems(["ООО", "АО", "ОАО", "ИП", "ЗАО"])
        if supplier:
            self.type_input.setCurrentText(supplier.tip_postavshika.value)
        layout.addRow("Тип поставщика:", self.type_input)

        self.phone_input = QLineEdit()
        # Устанавливаем маску после установки текста
        if supplier and supplier.kontakt_tel:
            self.phone_input.setText(supplier.kontakt_tel)
        self.phone_input.setInputMask("+7 (999) 999-99-99")  # Маска для телефона
        self.phone_input.setPlaceholderText("+7 (777) 777-77-77")  # Подсказка
        layout.addRow("Контактный телефон:", self.phone_input)

        self.email_input = QLineEdit()
        email_regex = QRegularExpression(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        email_validator = QRegularExpressionValidator(email_regex, self)
        self.email_input.setValidator(email_validator)
        self.email_input.setPlaceholderText("email@gmail.com")  # Подсказка
        if supplier and supplier.email:
            self.email_input.setText(supplier.email)
        layout.addRow("Email:", self.email_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Город, Улица, Номер дома")
        if supplier and supplier.juridicheskij_adres_rel:
            address_str = (
                f"{supplier.juridicheskij_adres_rel.ulica.gorod.nazvanie}, "
                f"{supplier.juridicheskij_adres_rel.ulica.nazvanie}, "
                f"{supplier.juridicheskij_adres_rel.nomer}"
            )
            self.address_input.setText(address_str)
        layout.addRow("Юридический адрес:", self.address_input)

        buttons_layout = QHBoxLayout()
        self.submit_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        buttons_layout.addWidget(self.submit_button)
        buttons_layout.addSpacing(10)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)

        self.setLayout(layout)
        print("SupplierForm инициализирована.")

class ProductForm(QWidget):
    def __init__(self, parent=None, product=None, suppliers=None):
        super().__init__(parent)
        self.setObjectName("formWidget")
        self.product = product
        self.suppliers = suppliers
        self.image_path = None  # Для хранения пути к выбранному изображению

        layout = QFormLayout()
        layout.setSpacing(10)

        self.title_label = QLabel("Товар" if product else "Добавить товар")
        self.title_label.setObjectName("titleLabel")
        layout.addRow(self.title_label)

        self.type_input = QComboBox()
        self.type_input.addItems([
            "Букет", "Цветок", "Композиция", "На свадьбу", 
            "Комнатные растения", "Флорариумы", "Подарки", "Популярное"
        ])
        if product:
            self.type_input.setCurrentText(product.nazvanie.value)
        layout.addRow("Тип товара:", self.type_input)

        self.number_input = QLineEdit()
        self.number_input.setValidator(QIntValidator(1, 999999, self))
        self.number_input.setText(str(product.nomer) if product else "1")
        layout.addRow("Номер товара:", self.number_input)

        self.description_input = QLineEdit()
        self.description_input.setText(product.opisanie if product else "")
        layout.addRow("Описание:", self.description_input)

        self.price_input = QLineEdit()
        self.price_input.setText(str(product.cena) if product else "0.00")
        layout.addRow("Цена:", self.price_input)

        self.supplier_input = QComboBox()
        if suppliers:
            self.supplier_input.addItems([s.nazvanie_postavshika for s in suppliers])
            if product and product.postavshik:
                self.supplier_input.setCurrentText(product.postavshik.nazvanie_postavshika)
        layout.addRow("Поставщик:", self.supplier_input)

        self.image_input = QLineEdit()
        self.image_input.setReadOnly(True)
        self.image_button = QPushButton("Выбрать изображение")
        self.image_menu = QMenu(self)
        self.select_file_action = QAction("Выбрать файл", self)
        self.paste_screenshot_action = QAction("Вставить скриншот", self)
        self.image_menu.addAction(self.select_file_action)
        self.image_menu.addAction(self.paste_screenshot_action)
        self.select_file_action.triggered.connect(self.select_image)
        self.paste_screenshot_action.triggered.connect(self.paste_screenshot)
        self.image_button.clicked.connect(self.show_image_menu)
        layout.addRow("Изображение:", self.image_input)
        layout.addWidget(self.image_button)

        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)  # Размер поля отображения: 150x150 пикселей
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #D2B48C; border-radius: 5px;")
        layout.addRow(self.image_label)

        if product and product.kartinka:
            temp_image_path = "temp_image.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(product.kartinka)
            pixmap = QPixmap(temp_image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
                self.image_path = temp_image_path
                self.image_input.setText(temp_image_path)
            else:
                print("Ошибка: не удалось загрузить изображение из базы данных")

        buttons_layout = QHBoxLayout()
        self.submit_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        buttons_layout.addWidget(self.submit_button)
        buttons_layout.addSpacing(10)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)

        self.setLayout(layout)
        print("ProductForm инициализирована.")

    def show_image_menu(self):
        self.image_menu.exec_(self.image_button.mapToGlobal(QPoint(0, self.image_button.height())))

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            self.image_input.setText(file_name)
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
            else:
                print(f"Ошибка: не удалось загрузить изображение {file_name}")
            print(f"Выбрано изображение: {file_name}")

    def paste_screenshot(self):
        # Получаем изображение из буфера обмена
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("В буфере обмена нет изображения!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        # Масштабируем изображение до размера поля отображения (150x150 пикселей)
        scaled_image = image.scaled(150, 150, Qt.KeepAspectRatio)

        # Сохраняем масштабированное изображение как временный файл
        temp_image_path = "temp_screenshot.jpg"
        if scaled_image.save(temp_image_path, "JPG"):
            self.image_path = temp_image_path
            self.image_input.setText(temp_image_path)
            pixmap = QPixmap(temp_image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
                print(f"Скриншот успешно масштабирован, вставлен и сохранён как {temp_image_path}")
            else:
                print(f"Ошибка: не удалось загрузить масштабированный скриншот из {temp_image_path}")
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Не удалось сохранить масштабированный скриншот!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            print("Ошибка: не удалось сохранить масштабированный скриншот как временный файл")

class ProductDetailsForm(QWidget):
    def __init__(self, parent=None, product=None, main_window=None):
        super().__init__(parent)
        self.setObjectName("detailsFormWidget")
        self.product = product
        self.main_window = main_window  # Ссылка на MainWindow для вызова clear_sidebar

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop)

        # Заголовок "Краткое описание"
        self.form_title_label = QLabel("Краткое описание")
        self.form_title_label.setObjectName("detailsFormTitleLabel")
        layout.addWidget(self.form_title_label)

        # Название категории товара (например, "Подарки", "Букеты")
        self.category_label = QLabel(product.nazvanie.value if product else "Категория не указана")
        self.category_label.setObjectName("detailsCategoryLabel")
        layout.addWidget(self.category_label)

        # Описание товара
        self.description_label = QLabel("Описание:")
        self.description_label.setObjectName("detailsLabel")
        layout.addWidget(self.description_label)

        self.description_text = QLabel(product.opisanie if product and product.opisanie else "Описание отсутствует")
        self.description_text.setObjectName("detailsTextLabel")
        self.description_text.setWordWrap(True)  # Перенос текста
        layout.addWidget(self.description_text)

        # Изображение товара
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)  # Размер изображения
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #5C4033; border-radius: 8px; background-color: #FFF5E6;")
        layout.addWidget(self.image_label)

        # Если у товара есть изображение, отображаем его
        if product and product.kartinka:
            temp_image_path = "temp_image_details.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(product.kartinka)
            pixmap = QPixmap(temp_image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("Не удалось загрузить изображение")
                print("Ошибка: не удалось загрузить изображение из базы данных")
        else:
            self.image_label.setText("Изображение отсутствует")

        # Кнопка "Закрыть"
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close_form)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        print("ProductDetailsForm инициализирована.")

    def close_form(self):
        # Закрываем форму, вызывая clear_sidebar у MainWindow
        if self.main_window:
            self.main_window.clear_sidebar()
        else:
            print("Ошибка: main_window не передан в ProductDetailsForm")

class EmployeeForm(QWidget):
    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self.setObjectName("formWidget")
        self.employee = employee

        layout = QFormLayout()
        layout.setSpacing(10)

        self.title_label = QLabel("Сотрудник" if employee else "Добавить сотрудника")
        self.title_label.setObjectName("titleLabel")
        layout.addRow(self.title_label)

        self.last_name_input = QLineEdit()
        self.last_name_input.setText(employee.familiya if employee else "")
        layout.addRow("Фамилия:", self.last_name_input)

        self.first_name_input = QLineEdit()
        self.first_name_input.setText(employee.imya if employee else "")
        layout.addRow("Имя:", self.first_name_input)

        self.middle_name_input = QLineEdit()
        self.middle_name_input.setText(employee.otchestvo if employee else "")
        layout.addRow("Отчество:", self.middle_name_input)

        self.gender_input = QComboBox()
        self.gender_input.addItems(["Мужской", "Женский"])
        if employee:
            self.gender_input.setCurrentText(employee.pol.value)
        layout.addRow("Пол:", self.gender_input)

        buttons_layout = QHBoxLayout()
        self.submit_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        buttons_layout.addWidget(self.submit_button)
        buttons_layout.addSpacing(10)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)

        self.setLayout(layout)
        print("EmployeeForm инициализирована.")

class DateSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор даты для отчета по поступлению")
        self.setFixedSize(400, 200)  # Увеличиваем ширину с 300 до 400

        self.russian_locale = QLocale(QLocale.Russian, QLocale.Russia)
        QLocale.setDefault(self.russian_locale)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("Выберите дату для отчета по поступлению товаров")
        self.title_label.setObjectName("greetingLabel")
        self.title_label.setWordWrap(True)  # Включаем перенос текста
        layout.addWidget(self.title_label)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setLocale(self.russian_locale)
        self.date_edit.setDisplayFormat("d MMMM yyyy")
        layout.addWidget(self.date_edit)

        self.submit_button = QPushButton("Подтвердить")
        self.submit_button.clicked.connect(self.accept)
        layout.addWidget(self.submit_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                print("Стили для DateSelectionDialog успешно загружены!")
        except FileNotFoundError:
            msg = QMessageBox(self)
            msg.setWindowTitle("Предупреждение")
            msg.setText("Файл styles.qss не найден. Стили не применены.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при загрузке стилей: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

    def get_selected_date(self):
        return self.date_edit.date()

class MainWindow(QMainWindow):
    def __init__(self, user_role):
        super().__init__()
        self.setWindowTitle("Привет, я букет!")
        self.setMinimumSize(QSize(1400, 750))
        self.setWindowIcon(QIcon("logo.png"))

        self.user_role = user_role

        try:
            self.session = Connect.create_session()
            print("Подключение к базе данных успешно!")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось подключиться к базе данных: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

        try:
            pdfmetrics.registerFont(TTFont('TimesNewRoman', 'times.ttf'))
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось зарегистрировать шрифт: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.top_layout = QHBoxLayout()
        self.main_layout.addLayout(self.top_layout)

        self.account_label = QLabel("Директор" if user_role == "direktor" else "Оператор-флорист")
        self.account_label.setObjectName("accountLabel")
        self.account_label.setAlignment(Qt.AlignRight)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.account_label)

        self.account_menu = QMenu(self)
        self.logout_action = QAction("Выход из учетной записи", self)
        self.exit_action = QAction("Выход из программы", self)
        self.account_menu.addAction(self.logout_action)
        self.account_menu.addAction(self.exit_action)

        self.logout_action.triggered.connect(self.logout)
        self.exit_action.triggered.connect(self.exit_program)

        self.account_label.mousePressEvent = self.show_account_menu

        self.content_layout = QHBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        self.tabs = QTabWidget()
        self.custom_tab_bar = CustomTabBar()
        self.tabs.setTabBar(self.custom_tab_bar)
        self.content_layout.addWidget(self.tabs, stretch=3)

        self.sidebar_widget = ResizableSidebar(self)
        self.sidebar_layout = self.sidebar_widget.layout
        self.content_layout.addWidget(self.sidebar_widget, stretch=1)

        self.hide_sidebar()

        self.suppliers_tab = QWidget()
        self.tabs.addTab(self.suppliers_tab, "Поставщики")
        self.suppliers_layout = QVBoxLayout(self.suppliers_tab)
        self.suppliers_table = QTableWidget()
        self.suppliers_layout.addWidget(self.suppliers_table)

        if self.user_role == "direktor":
            self.supplier_buttons_layout = QHBoxLayout()
            self.add_supplier_button = QPushButton("Добавить поставщика")
            self.edit_supplier_button = QPushButton("Редактировать поставщика")
            self.delete_supplier_button = QPushButton("Удалить поставщика")
            self.supplier_buttons_layout.addWidget(self.add_supplier_button)
            self.supplier_buttons_layout.addWidget(self.edit_supplier_button)
            self.supplier_buttons_layout.addWidget(self.delete_supplier_button)
            self.suppliers_layout.addLayout(self.supplier_buttons_layout)

            self.add_supplier_button.clicked.connect(self.add_supplier)
            self.edit_supplier_button.clicked.connect(self.edit_supplier)
            self.delete_supplier_button.clicked.connect(self.delete_supplier)

        self.products_tab = QWidget()
        self.tabs.addTab(self.products_tab, "Товары")
        self.products_layout = QVBoxLayout(self.products_tab)
        self.products_table = QTableWidget()
        self.products_layout.addWidget(self.products_table)

        if self.user_role == "direktor":
            self.product_buttons_layout = QHBoxLayout()
            self.add_product_button = QPushButton("Добавить товар")
            self.edit_product_button = QPushButton("Редактировать товар")
            self.delete_product_button = QPushButton("Удалить товар")
            self.product_buttons_layout.addWidget(self.add_product_button)
            self.product_buttons_layout.addWidget(self.edit_product_button)
            self.product_buttons_layout.addWidget(self.delete_product_button)
            self.products_layout.addLayout(self.product_buttons_layout)

            self.add_product_button.clicked.connect(self.add_product)
            self.edit_product_button.clicked.connect(self.edit_product)
            self.delete_product_button.clicked.connect(self.delete_product)

        self.employees_tab = QWidget()
        self.tabs.addTab(self.employees_tab, "Сотрудники")
        self.employees_layout = QVBoxLayout(self.employees_tab)
        self.employees_table = QTableWidget()
        self.employees_layout.addWidget(self.employees_table)

        if self.user_role == "direktor":
            self.employee_buttons_layout = QHBoxLayout()
            self.add_employee_button = QPushButton("Добавить сотрудника")
            self.edit_employee_button = QPushButton("Редактировать сотрудника")
            self.delete_employee_button = QPushButton("Удалить сотрудника")
            self.employee_buttons_layout.addWidget(self.add_employee_button)
            self.employee_buttons_layout.addWidget(self.edit_employee_button)
            self.employee_buttons_layout.addWidget(self.delete_employee_button)
            self.employees_layout.addLayout(self.employee_buttons_layout)

            self.add_employee_button.clicked.connect(self.add_employee)
            self.edit_employee_button.clicked.connect(self.edit_employee)
            self.delete_employee_button.clicked.connect(self.delete_employee)

        self.reports_tab = QWidget()
        self.reports_index = self.tabs.addTab(self.reports_tab, "Отчеты")
        self.reports_layout = QVBoxLayout(self.reports_tab)
        self.reports_table = QTableWidget()
        self.reports_layout.addWidget(self.reports_table)

        self.reports_menu = QMenu(self)
        self.arrival_report_action = QAction("Отчет по поступлению товаров", self)
        self.stock_report_action = QAction("Отчет по остаткам товаров", self)
        self.loss_report_action = QAction("Отчет по убытию товаров", self)
        self.order_conversion_report_action = QAction("Бланк заказа", self)
        self.reports_menu.addAction(self.order_conversion_report_action)
        self.order_conversion_report_action.triggered.connect(self.load_order_conversion_reports)
        
        # Новые действия для отчетов
        self.general_accounting_report_action = QAction("Общий учет", self)
        self.invoice_report_action = QAction("Счет-фактура", self)
        self.specification_report_action = QAction("Спецификация", self)
        
        # Добавляем новые действия в меню отчетов
        self.reports_menu.addAction(self.general_accounting_report_action)
        self.reports_menu.addAction(self.invoice_report_action)
        self.reports_menu.addAction(self.specification_report_action)
        
        # Подключаем обработчики
        self.general_accounting_report_action.triggered.connect(self.generate_general_accounting_report)
        self.invoice_report_action.triggered.connect(self.generate_invoice_report)
        self.specification_report_action.triggered.connect(self.generate_specification_report)
        
        self.reports_menu.addAction(self.arrival_report_action)
        self.reports_menu.addAction(self.stock_report_action)
        self.reports_menu.addAction(self.loss_report_action)

        self.arrival_report_action.triggered.connect(self.load_arrival_reports)
        self.stock_report_action.triggered.connect(self.load_stock_reports)
        self.loss_report_action.triggered.connect(self.load_loss_reports)

        self.custom_tab_bar.set_reports_menu(self.reports_menu, self.reports_index)

        self.tabs.currentChanged.connect(self.handle_tab_change)

        self.report_buttons_layout = QHBoxLayout()
        self.generate_report_button = QPushButton("Сформировать отчет")
        self.generate_report_button.clicked.connect(self.generate_pdf_report)
        self.report_buttons_layout.addWidget(self.generate_report_button)
        self.reports_layout.addLayout(self.report_buttons_layout)

        try:
            self.load_suppliers_data()
            self.load_products_data()
            self.load_employees_data()
            self.reports_table.setRowCount(0)
            self.reports_table.setColumnCount(0)
            self.current_report_type = None
            print("Данные успешно загружены!")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при загрузке данных: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                print("Стили успешно загружены!")
                print("Первые 100 символов стилей:", stylesheet[:100])
        except FileNotFoundError:
            msg = QMessageBox(self)
            msg.setWindowTitle("Предупреждение")
            msg.setText("Файл styles.qss не найден. Стили не применены.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при загрузке стилей: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

    def clear_sidebar(self):
        for i in reversed(range(self.sidebar_layout.count())):
            widget = self.sidebar_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.hide_sidebar()

    def show_sidebar(self):
        self.sidebar_widget.setVisible(True)
        if self.sidebar_widget.width() == 0:
            self.sidebar_widget.setFixedWidth(300)
        else:
            self.sidebar_widget.setFixedWidth(self.sidebar_widget.width())
        print(f"Панель показана с шириной: {self.sidebar_widget.width()} пикселей")

    def hide_sidebar(self):
        self.sidebar_widget.setVisible(False)
        self.sidebar_widget.setFixedWidth(0)
        print("Панель скрыта.")

    def show_account_menu(self, event):
        if event.button() == Qt.LeftButton:
            self.account_menu.exec_(self.account_label.mapToGlobal(QPoint(0, self.account_label.height())))

    def logout(self):
        self.close()
        self.auth_window = AuthWindow()
        self.auth_window.show()

    def exit_program(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Подтверждение")
        msg.setText("Вы уверены, что хотите выйти из программы?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("Да")
        msg.button(QMessageBox.No).setText("Нет")
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            QApplication.quit()

    def load_suppliers_data(self):
        suppliers = self.session.query(Postavshik).all()
        self.suppliers_table.setRowCount(len(suppliers))
        self.suppliers_table.setColumnCount(6)
        self.suppliers_table.setHorizontalHeaderLabels([
            "№", "Название", "Тип", "Телефон", "Email", "Юридический адрес"
        ])

        for row, supplier in enumerate(suppliers):
            self.suppliers_table.setItem(row, 0, QTableWidgetItem(str(supplier.id)))
            self.suppliers_table.setItem(row, 1, QTableWidgetItem(supplier.nazvanie_postavshika))
            self.suppliers_table.setItem(row, 2, QTableWidgetItem(supplier.tip_postavshika.value))
            self.suppliers_table.setItem(row, 3, QTableWidgetItem(supplier.kontakt_tel or ""))
            self.suppliers_table.setItem(row, 4, QTableWidgetItem(supplier.email or ""))
            address_str = ""
            if supplier.juridicheskij_adres_rel:
                address_str = (
                    f"{supplier.juridicheskij_adres_rel.ulica.gorod.nazvanie}, "
                    f"{supplier.juridicheskij_adres_rel.ulica.nazvanie}, "
                    f"{supplier.juridicheskij_adres_rel.nomer}"
                )
            self.suppliers_table.setItem(row, 5, QTableWidgetItem(address_str))

        self.suppliers_table.resizeColumnsToContents()

    def add_supplier(self):
        print("Открытие формы добавления поставщика...")
        self.clear_sidebar()
        self.show_sidebar()
        form = SupplierForm(self)
        self.sidebar_layout.addWidget(form)
        form.submit_button.clicked.connect(lambda: self.save_supplier(form))
        form.cancel_button.clicked.connect(self.clear_sidebar)

    def edit_supplier(self):
        print("Открытие формы редактирования поставщика...")
        try:
            selected = self.suppliers_table.currentRow()
            if selected < 0:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Выберите поставщика для редактирования!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            supplier_id = int(self.suppliers_table.item(selected, 0).text())
            supplier = self.session.query(Postavshik).filter_by(id=supplier_id).first()
            if not supplier:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Поставщик не найден!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            self.clear_sidebar()
            self.show_sidebar()
            form = SupplierForm(self, supplier=supplier)
            self.sidebar_layout.addWidget(form)
            form.submit_button.clicked.connect(lambda: self.save_supplier(form, supplier))
            form.cancel_button.clicked.connect(self.clear_sidebar)
            print("Форма редактирования поставщика успешно открыта.")
        except Exception as e:
            print(f"Ошибка при открытии формы редактирования поставщика: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при открытии формы редактирования поставщика: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def save_supplier(self, form, supplier=None):
        try:
            phone = form.phone_input.text().strip()
            email = form.email_input.text().strip()

            # Проверка телефона: считаем, что поле пустое, если в нём только символы маски
            phone_cleaned = ''.join(filter(str.isdigit, phone))
            if not phone_cleaned:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите корректный контактный телефон!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Да")
                msg.exec_()
                return

            # Проверка email: email обязателен и должен соответствовать формату
            if not email or not form.email_input.hasAcceptableInput():
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите корректный email!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Да")
                msg.exec_()
                return

            address_text = form.address_input.text().strip()
            if not address_text:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите юридический адрес!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            try:
                city_name, street_name, house_number = [part.strip() for part in address_text.split(",", 2)]
                house_number = int(house_number)
            except ValueError:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Неверный формат адреса! Используйте: Город, Улица, Номер дома")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            city = self.session.query(Gorod).filter_by(nazvanie=city_name).first()
            if not city:
                city = Gorod(nazvanie=city_name, sok_nazvanie=city_name[:3], oblast_id=1)
                self.session.add(city)
                self.session.commit()

            street = self.session.query(Ulica).filter_by(nazvanie=street_name, gorod_id=city.id).first()
            if not street:
                street = Ulica(nazvanie=street_name, gorod_id=city.id)
                self.session.add(street)
                self.session.commit()

            house = self.session.query(DomStroenie).filter_by(nomer=house_number, ulica_id=street.id).first()
            if not house:
                house = DomStroenie(nomer=house_number, ulica_id=street.id)
                self.session.add(house)
                self.session.commit()

            if supplier:
                supplier.nazvanie_postavshika = form.name_input.text()
                supplier.tip_postavshika = TipPostavshika(form.type_input.currentText())
                supplier.kontakt_tel = phone
                supplier.email = email
                supplier.juridicheskij_adres = house.id
                self.session.commit()
                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Поставщик обновлен!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
            else:
                new_supplier = Postavshik(
                    nazvanie_postavshika=form.name_input.text(),
                    tip_postavshika=TipPostavshika(form.type_input.currentText()),
                    kontakt_tel=phone,
                    email=email,
                    juridicheskij_adres=house.id
                )
                self.session.add(new_supplier)
                self.session.commit()
                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Поставщик добавлен!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()

            self.load_suppliers_data()
            self.clear_sidebar()

        except Exception as e:
            print(f"Ошибка при сохранении поставщика: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при сохранении поставщика: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def delete_supplier(self):
        selected = self.suppliers_table.currentRow()
        if selected < 0:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Выберите поставщика для удаления!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        supplier_id = int(self.suppliers_table.item(selected, 0).text())
        supplier = self.session.query(Postavshik).filter_by(id=supplier_id).first()
        if not supplier:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Поставщик не найден!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Подтверждение")
        msg.setText("Вы уверены, что хотите удалить поставщика?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("Да")
        msg.button(QMessageBox.No).setText("Нет")
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            self.session.delete(supplier)
            self.session.commit()
            self.load_suppliers_data()
            msg_success = QMessageBox(self)
            msg_success.setWindowTitle("Успех")
            msg_success.setText("Поставщик удален!")
            msg_success.setStandardButtons(QMessageBox.Ok)
            msg_success.button(QMessageBox.Ok).setText("Хорошо")
            msg_success.exec_()

    def load_products_data(self):
        products = self.session.query(Tovar).all()
        self.products_table.setRowCount(len(products))
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([
            "№", "Тип", "Номер", "Описание", "Цена", "Поставщик"
        ])

        for row, product in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(str(product.id)))
            self.products_table.setItem(row, 1, QTableWidgetItem(product.nazvanie.value))
            self.products_table.setItem(row, 2, QTableWidgetItem(str(product.nomer)))
            self.products_table.setItem(row, 3, QTableWidgetItem(product.opisanie or ""))
            self.products_table.setItem(row, 4, QTableWidgetItem(str(product.cena) if product.cena else ""))
            self.products_table.setItem(row, 5, QTableWidgetItem(product.postavshik.nazvanie_postavshika if product.postavshik else ""))

        self.products_table.resizeColumnsToContents()
        # Подключаем обработчик двойного нажатия
        self.products_table.doubleClicked.connect(self.show_product_details)

    def show_product_details(self):
        print("Двойное нажатие на таблицу товаров...")
        selected = self.products_table.currentRow()
        if selected < 0:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Выберите товар для просмотра деталей!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        product_id = int(self.products_table.item(selected, 0).text())
        product = self.session.query(Tovar).filter_by(id=product_id).first()
        if not product:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Товар не найден!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        self.clear_sidebar()
        self.show_sidebar()
        form = ProductDetailsForm(self, product=product, main_window=self)  # Передаём self как main_window
        self.sidebar_layout.addWidget(form)
        print(f"Открыта форма деталей для товара ID: {product_id}")

    def add_product(self):
        print("Открытие формы добавления товара...")
        try:
            suppliers = self.session.query(Postavshik).all()
            if not suppliers:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Сначала добавьте поставщика!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            self.clear_sidebar()
            self.show_sidebar()
            form = ProductForm(self, product=None, suppliers=suppliers)
            self.sidebar_layout.addWidget(form)
            form.submit_button.clicked.connect(lambda: self.save_product(form, suppliers))
            form.cancel_button.clicked.connect(self.clear_sidebar)
            print("Форма добавления товара успешно открыта.")
        except Exception as e:
            print(f"Ошибка при открытии формы добавления товара: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при открытии формы добавления товара: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def edit_product(self):
        print("Открытие формы редактирования товара...")
        try:
            selected = self.products_table.currentRow()
            if selected < 0:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Выберите товар для редактирования!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            product_id = int(self.products_table.item(selected, 0).text())
            product = self.session.query(Tovar).filter_by(id=product_id).first()
            if not product:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Товар не найден!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            suppliers = self.session.query(Postavshik).all()
            if not suppliers:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Нет доступных поставщиков!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            self.clear_sidebar()
            self.show_sidebar()
            form = ProductForm(self, product=product, suppliers=suppliers)
            self.sidebar_layout.addWidget(form)
            form.submit_button.clicked.connect(lambda: self.save_product(form, suppliers, product))
            form.cancel_button.clicked.connect(self.clear_sidebar)
            print("Форма редактирования товара успешно открыта.")
        except Exception as e:
            print(f"Ошибка при открытии формы редактирования товара: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при открытии формы редактирования товара: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def save_product(self, form, suppliers, product=None):
        try:
            image_data = None
            if form.image_path:
                with open(form.image_path, "rb") as f:
                    image_data = f.read()

            # Валидация данных
            price_text = form.price_input.text().strip()
            number_text = form.number_input.text().strip()
            
            try:
                price = float(price_text) if price_text else None
                if price is not None and price < 0:
                    raise ValueError("Цена не может быть отрицательной!")
            except ValueError:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите корректную цену (число) или оставьте поле пустым!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            try:
                nomer = int(number_text) if number_text else 1
                if nomer <= 0:
                    raise ValueError("Номер товара должен быть положительным!")
            except ValueError:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите корректный номер товара (целое число)!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            if product:
                product.nazvanie = TipTovara(form.type_input.currentText())
                product.nomer = nomer
                product.opisanie = form.description_input.text()
                product.cena = price
                product.kartinka = image_data if image_data else product.kartinka
                product.postavshik_id = suppliers[form.supplier_input.currentIndex()].id
                self.session.commit()
                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Товар обновлен!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                print("Товар успешно обновлён.")
            else:
                new_product = Tovar(
                    nazvanie=TipTovara(form.type_input.currentText()),
                    nomer=nomer,
                    opisanie=form.description_input.text(),
                    cena=price,
                    kartinka=image_data,
                    postavshik_id=suppliers[form.supplier_input.currentIndex()].id
                )
                self.session.add(new_product)
                self.session.commit()
                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Товар добавлен!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                print("Товар успешно добавлен.")

            self.load_products_data()
            self.clear_sidebar()

        except Exception as e:
            print(f"Ошибка при сохранении товара: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при сохранении товара: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def delete_product(self):
        print("Попытка удаления товара...")
        try:
            selected = self.products_table.currentRow()
            if selected < 0:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Выберите товар для удаления!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            product_id = int(self.products_table.item(selected, 0).text())
            product = self.session.query(Tovar).filter_by(id=product_id).first()
            if not product:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Товар не найден!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            msg = QMessageBox(self)
            msg.setWindowTitle("Подтверждение")
            msg.setText("Вы уверены, что хотите удалить товар?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.button(QMessageBox.Yes).setText("Да")
            msg.button(QMessageBox.No).setText("Нет")
            reply = msg.exec_()
            if reply == QMessageBox.Yes:
                self.session.delete(product)
                self.session.commit()
                self.load_products_data()
                msg_success = QMessageBox(self)
                msg_success.setWindowTitle("Успех")
                msg_success.setText("Товар удален!")
                msg_success.setStandardButtons(QMessageBox.Ok)
                msg_success.button(QMessageBox.Ok).setText("Хорошо")
                msg_success.exec_()
                print("Товар успешно удалён.")
        except Exception as e:
            print(f"Ошибка при удалении товара: {str(e)}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Произошла ошибка при удалении товара: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def load_employees_data(self):
        employees = self.session.query(Sotrudnik).all()
        self.employees_table.setRowCount(len(employees))
        self.employees_table.setColumnCount(5)
        self.employees_table.setHorizontalHeaderLabels([
            "№", "Фамилия", "Имя", "Отчество", "Пол"
        ])

        for row, employee in enumerate(employees):
            self.employees_table.setItem(row, 0, QTableWidgetItem(str(employee.id)))
            self.employees_table.setItem(row, 1, QTableWidgetItem(employee.familiya))
            self.employees_table.setItem(row, 2, QTableWidgetItem(employee.imya))
            self.employees_table.setItem(row, 3, QTableWidgetItem(employee.otchestvo or ""))
            self.employees_table.setItem(row, 4, QTableWidgetItem(employee.pol.value))

        self.employees_table.resizeColumnsToContents()

    def add_employee(self):
        print("Открытие формы добавления сотрудника...")
        self.clear_sidebar()
        self.show_sidebar()
        form = EmployeeForm(self)
        self.sidebar_layout.addWidget(form)
        form.submit_button.clicked.connect(lambda: self.save_employee(form))
        form.cancel_button.clicked.connect(self.clear_sidebar)

    def edit_employee(self):
        print("Открытие формы редактирования сотрудника...")
        selected = self.employees_table.currentRow()
        if selected < 0:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Выберите сотрудника для редактирования!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        employee_id = int(self.employees_table.item(selected, 0).text())
        employee = self.session.query(Sotrudnik).filter_by(id=employee_id).first()
        if not employee:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Сотрудник не найден!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        self.clear_sidebar()
        self.show_sidebar()
        form = EmployeeForm(self, employee=employee)
        self.sidebar_layout.addWidget(form)
        form.submit_button.clicked.connect(lambda: self.save_employee(form, employee))
        form.cancel_button.clicked.connect(self.clear_sidebar)

    def save_employee(self, form, employee=None):
        if employee:
            employee.familiya = form.last_name_input.text()
            employee.imya = form.first_name_input.text()
            employee.otchestvo = form.middle_name_input.text()
            employee.pol = Pol(form.gender_input.currentText())
            self.session.commit()
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText("Сотрудник обновлен!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
        else:
            new_employee = Sotrudnik(
                familiya=form.last_name_input.text(),
                imya=form.first_name_input.text(),
                otchestvo=form.middle_name_input.text(),
                pol=Pol(form.gender_input.currentText())
            )
            self.session.add(new_employee)
            self.session.commit()
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText("Сотрудник добавлен!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

        self.load_employees_data()
        self.clear_sidebar()

    def delete_employee(self):
        selected = self.employees_table.currentRow()
        if selected < 0:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Выберите сотрудника для удаления!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        employee_id = int(self.employees_table.item(selected, 0).text())
        employee = self.session.query(Sotrudnik).filter_by(id=employee_id).first()
        if not employee:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Сотрудник не найден!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Подтверждение")
        msg.setText("Вы уверены, что хотите удалить сотрудника?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("Да")
        msg.button(QMessageBox.No).setText("Нет")
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            self.session.delete(employee)
            self.session.commit()
            self.load_employees_data()
            msg_success = QMessageBox(self)
            msg_success.setWindowTitle("Успех")
            msg_success.setText("Сотрудник удален!")
            msg_success.setStandardButtons(QMessageBox.Ok)
            msg_success.button(QMessageBox.Ok).setText("Хорошо")
            msg_success.exec_()

    def load_arrival_reports(self):
        self.current_report_type = "arrival"
        date_dialog = DateSelectionDialog(self)
        date_dialog.setWindowTitle("Выбор даты для отчета по поступлению")
        date_dialog.title_label.setText("Выберите дату для отчета по поступлению товаров")
        if date_dialog.exec_() == QDialog.Accepted:
            selected_qdate = date_dialog.get_selected_date()
            self.selected_arrival_date_obj = selected_qdate.toPython()  # Сохраняем как datetime.date

            # Локализация для русского языка
            locale = QLocale(QLocale.Russian, QLocale.Russia)
            self.selected_arrival_date = locale.toString(selected_qdate, "d MMMM yyyy") + "г"  # Форматируем дату с русским месяцем

            # Загружаем существующие отчеты по поступлению за выбранную дату
            reports = self.session.query(OtchetyPoPostuplenijuTovarov).filter(
                OtchetyPoPostuplenijuTovarov.data_postuplenija == self.selected_arrival_date_obj
            ).all()

            # Загружаем все товары из таблицы Tovar
            products = self.session.query(Tovar).all()

            # Сохраняем список товаров для дальнейшего использования (например, в PDF)
            self.arrival_products = products

            # Формируем таблицу
            self.reports_table.setRowCount(len(products))
            self.reports_table.setColumnCount(6)
            self.reports_table.setHorizontalHeaderLabels([
                "№", "Дата поступления", "Количество", "Товар", "Описание", "Поставщик"
            ])

            # Создаем словарь для быстрого поиска существующих отчетов
            existing_reports = {report.tovar_id: report for report in reports if report.tovar_id}

            for row, product in enumerate(products):
                # № (порядковый номер строки, начиная с 1)
                self.reports_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.reports_table.item(row, 0).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Проверяем, есть ли отчет для этого товара
                report = existing_reports.get(product.id)

                # Дата поступления: редактируемая, из отчета или выбранная дата по умолчанию
                date_str = str(report.data_postuplenija) if report else str(self.selected_arrival_date_obj)
                date_item = QTableWidgetItem(date_str)
                self.reports_table.setItem(row, 1, date_item)

                # Количество: редактируемое, из отчета или 0 по умолчанию
                quantity = report.kolithestvo_postupivshih_tovarov if report else 0
                quantity_item = QTableWidgetItem(str(quantity))
                self.reports_table.setItem(row, 2, quantity_item)

                # Товар: берем из Tovar.nazvanie
                self.reports_table.setItem(row, 3, QTableWidgetItem(product.nazvanie.value if product.nazvanie else ""))
                self.reports_table.item(row, 3).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Описание: берем из Tovar.opisanie
                self.reports_table.setItem(row, 4, QTableWidgetItem(product.opisanie if product.opisanie else ""))
                self.reports_table.item(row, 4).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Поставщик: берем из Postavshik.nazvanie_postavshika
                self.reports_table.setItem(row, 5, QTableWidgetItem(product.postavshik.nazvanie_postavshika if product.postavshik else ""))
                self.reports_table.item(row, 5).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

            self.reports_table.resizeColumnsToContents()

            # Подключаем обработчик изменения данных
            self.reports_table.itemChanged.connect(self.update_arrival_report)

            # Добавляем контекстное меню для удаления строк
            self.reports_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.reports_table.customContextMenuRequested.connect(self.show_arrival_context_menu)

        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Отмена")
            msg.setText("Формирование отчета по поступлению товаров отменено.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def load_loss_reports(self):
        self.current_report_type = "loss"
        date_dialog = DateSelectionDialog(self)
        date_dialog.setWindowTitle("Выбор даты для отчета по убытию")
        date_dialog.title_label.setText("Выберите дату для отчета по убытию товаров")
        if date_dialog.exec_() == QDialog.Accepted:
            selected_qdate = date_dialog.get_selected_date()
            self.selected_loss_date_obj = selected_qdate.toPython()  # Сохраняем как datetime.date

            # Локализация для русского языка
            locale = QLocale(QLocale.Russian, QLocale.Russia)
            self.selected_loss_date = locale.toString(selected_qdate, "d MMMM yyyy") + "г"  # Форматируем дату с русским месяцем

            # Загружаем отчеты по убытию за выбранную дату
            reports = self.session.query(OtchetyPoUbytomuTovaru).filter(
                OtchetyPoUbytomuTovaru.data_formirovaniya_otcheta == self.selected_loss_date_obj
            ).all()

            self.reports_table.setRowCount(len(reports))
            self.reports_table.setColumnCount(5)
            self.reports_table.setHorizontalHeaderLabels([
                "№", "Дата убытия", "Количество убытого товара", "Дата отчета", "Товар"
            ])

            for row, report in enumerate(reports):
                self.reports_table.setItem(row, 0, QTableWidgetItem(str(report.id)))
                # Форматируем дату убытия
                date_loss_str = locale.toString(report.data_ubytija, "d MMMM yyyy") + "г"
                self.reports_table.setItem(row, 1, QTableWidgetItem(date_loss_str))
                self.reports_table.setItem(row, 2, QTableWidgetItem(str(report.kolithestvo_ubytogo_tovara)))
                # Форматируем дату отчета
                date_report_str = locale.toString(report.data_formirovaniya_otcheta, "d MMMM yyyy") + "г"
                self.reports_table.setItem(row, 3, QTableWidgetItem(date_report_str))
                self.reports_table.setItem(row, 4, QTableWidgetItem(report.tovar.nazvanie.value if report.tovar else ""))

            self.reports_table.resizeColumnsToContents()

            # Если данных нет, показываем сообщение
            if not reports:
                msg = QMessageBox(self)
                msg.setWindowTitle("Информация")
                msg.setText(f"Нет данных об убытии товаров на {self.selected_loss_date}.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()

        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Отмена")
            msg.setText("Формирование отчета по убытию товаров отменено.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            # Сбрасываем состояние
            self.current_report_type = None
            self.reports_table.setRowCount(0)
            self.reports_table.setColumnCount(0)

    def load_order_conversion_reports(self):
        self.current_report_type = "order_conversion"
        date_dialog = DateSelectionDialog(self)
        date_dialog.setWindowTitle("Выбор даты для бланка заказа")
        date_dialog.title_label.setText("Выберите дату для бланка заказа")
        if date_dialog.exec_() == QDialog.Accepted:
            selected_qdate = date_dialog.get_selected_date()
            self.selected_order_date_obj = selected_qdate.toPython()  # Сохраняем как datetime.date

            # Задаем локализацию на русский язык
            locale = QLocale(QLocale.Russian, QLocale.Russia)
            self.selected_order_date = locale.toString(selected_qdate, "d MMMM yyyy") + "г"  # Строковое представление для PDF

            # Загружаем все товары из таблицы Tovar
            products = self.session.query(Tovar).all()

            # Сохраняем список товаров для дальнейшего использования (например, в PDF)
            self.order_products = products

            # Формируем таблицу
            self.reports_table.setRowCount(len(products))
            self.reports_table.setColumnCount(7)  # Добавляем колонку "Условия получения"
            self.reports_table.setHorizontalHeaderLabels([
                "№ п/п", "Товар", "Количество", "Цена", "Сумма", "Возможная цена", "Условия получения"
            ])

            for row, product in enumerate(products):
                # № п/п (порядковый номер строки, начиная с 1)
                self.reports_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.reports_table.item(row, 0).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Товар: берем из Tovar.opisanie
                self.reports_table.setItem(row, 1, QTableWidgetItem(product.opisanie if product.opisanie else ""))
                self.reports_table.item(row, 1).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Количество: изначально 0, редактируемое
                quantity_item = QTableWidgetItem("0")
                self.reports_table.setItem(row, 2, quantity_item)

                # Цена: берем из Tovar.cena
                price = float(product.cena) if product.cena else 0.00
                self.reports_table.setItem(row, 3, QTableWidgetItem(f"{price:.2f}"))
                self.reports_table.item(row, 3).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Сумма: изначально 0 (Количество * Цена)
                self.reports_table.setItem(row, 4, QTableWidgetItem("0.00"))
                self.reports_table.item(row, 4).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Возможная цена: изначально 0 (Сумма * 0.03)
                self.reports_table.setItem(row, 5, QTableWidgetItem("0.00"))
                self.reports_table.item(row, 5).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

                # Условия получения: фиксированное значение "3% скидка"
                self.reports_table.setItem(row, 6, QTableWidgetItem("3% скидка"))
                self.reports_table.item(row, 6).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Запрещаем редактирование

            self.reports_table.resizeColumnsToContents()

            # Подключаем обработчик изменения количества
            self.reports_table.itemChanged.connect(self.update_order_totals)

            # Добавляем контекстное меню для удаления строк
            self.reports_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.reports_table.customContextMenuRequested.connect(self.show_context_menu)

        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Отмена")
            msg.setText("Формирование бланка заказа отменено.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def update_order_totals(self, item):
        # Проверяем, что изменена колонка "Количество" (индекс 2)
        if item.column() == 2:
            row = item.row()
            try:
                quantity = int(item.text())  # Получаем новое количество
                if quantity < 0:
                    quantity = 0
                    item.setText("0")
            except ValueError:
                quantity = 0
                item.setText("0")

            # Получаем цену (индекс 3)
            price_item = self.reports_table.item(row, 3)
            price = float(price_item.text()) if price_item else 0.00

            # Вычисляем сумму (Количество * Цена)
            total = quantity * price
            self.reports_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))

            # Вычисляем возможную цену (Сумма * 0.03)
            possible_price = total * 0.03
            self.reports_table.setItem(row, 5, QTableWidgetItem(f"{possible_price:.2f}"))

            # Обновляем № п/п после возможного удаления строк
            for i in range(self.reports_table.rowCount()):
                self.reports_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

    def update_arrival_report(self, item):
        # Проверяем, что изменена редактируемая колонка ("Дата поступления" или "Количество")
        if item.column() not in [1, 2]:  # Индексы колонок "Дата поступления" и "Количество"
            return

        row = item.row()
        product = self.arrival_products[row]  # Товар из списка

        # Получаем данные из таблицы
        date_str = self.reports_table.item(row, 1).text()  # Дата поступления
        quantity_str = self.reports_table.item(row, 2).text()  # Количество

        # Валидация и преобразование данных
        try:
            # Преобразуем строку даты в datetime.date
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Неверный формат даты! Используйте ГГГГ-ММ-ДД (например, 2025-04-12).")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            # Возвращаем исходное значение (self.selected_arrival_date_obj)
            item.setText(str(self.selected_arrival_date_obj))
            return

        try:
            quantity = int(quantity_str)
            if quantity < 0:
                raise ValueError("Количество не может быть отрицательным!")
        except ValueError:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Введите корректное количество (целое число, больше или равно 0)!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            item.setText("0")
            quantity = 0

        # Ищем существующий отчет для этого товара и даты
        report = self.session.query(OtchetyPoPostuplenijuTovarov).filter(
            OtchetyPoPostuplenijuTovarov.tovar_id == product.id,
            OtchetyPoPostuplenijuTovarov.data_postuplenija == date
        ).first()

        try:
            if report:
                # Обновляем существующий отчет
                report.data_postuplenija = date
                report.kolithestvo_postupivshih_tovarov = quantity
                report.data_formirovaniya_otcheta = self.selected_arrival_date_obj  # Устанавливаем дату формирования
            else:
                # Создаем новый отчет
                new_report = OtchetyPoPostuplenijuTovarov(
                    data_postuplenija=date,
                    kolithestvo_postupivshih_tovarov=quantity,
                    data_formirovaniya_otcheta=self.selected_arrival_date_obj,  # Устанавливаем дату формирования
                    tovar_id=product.id,
                    postavshik_id=product.postavshik_id
                )
                self.session.add(new_report)

            self.session.commit()
        except Exception as e:
            self.session.rollback()
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при сохранении отчета: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def show_context_menu(self, pos):
        # Показываем контекстное меню для удаления строк
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить строку")
        action = menu.exec_(self.reports_table.mapToGlobal(pos))

        if action == delete_action:
            selected_rows = sorted(set(index.row() for index in self.reports_table.selectedIndexes()), reverse=True)
            for row in selected_rows:
                self.reports_table.removeRow(row)
            # Обновляем № п/п после удаления
            for i in range(self.reports_table.rowCount()):
                self.reports_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                
    def show_arrival_context_menu(self, pos):
        # Показываем контекстное меню для удаления строк в отчете по поступлению
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить строку")
        action = menu.exec_(self.reports_table.mapToGlobal(pos))

        if action == delete_action:
            selected_rows = sorted(set(index.row() for index in self.reports_table.selectedIndexes()), reverse=True)
            for row in selected_rows:
                # Удаляем строку из таблицы
                self.reports_table.removeRow(row)
            # Обновляем № после удаления
            for i in range(self.reports_table.rowCount()):
                self.reports_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
    def update_stock_report(self, item):
        # Обрабатываем изменение только в колонках "Количество товара" (3) или "Срок годности" (4)
        if item.column() not in [3, 4]:
            return

        row = item.row()
        if row >= len(self.stock_products):
            return  # Проверка на случай, если строка удалена

        product = self.stock_products[row]  # Товар из сохраненного списка

        if item.column() == 3:  # Количество товара
            quantity_str = item.text()
            try:
                quantity = int(quantity_str)
                if quantity < 0:
                    raise ValueError("Количество не может быть отрицательным!")
            except ValueError:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Введите корректное количество (целое число, больше или равно 0)!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                item.setText("0")
                quantity = 0

            # Ищем существующий отчет
            report = self.session.query(OtchetyPoOstatkamTovarov).filter(
                OtchetyPoOstatkamTovarov.tovar_id == product.id,
                OtchetyPoOstatkamTovarov.data_formirovaniya_otcheta == self.selected_stock_date_obj
            ).first()

            try:
                if report:
                    # Обновляем существующий отчет
                    report.kolithestvo_tovara = quantity
                else:
                    # Создаем новый отчет
                    new_report = OtchetyPoOstatkamTovarov(
                        data_formirovaniya_otcheta=self.selected_stock_date_obj,
                        kolithestvo_tovara=quantity,
                        tovar_id=product.id
                    )
                    self.session.add(new_report)

                self.session.commit()
            except Exception as e:
                self.session.rollback()
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText(f"Ошибка при сохранении отчета: {str(e)}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()

        elif item.column() == 4:  # Срок годности
            expiry = item.text().strip()
            if not expiry:
                expiry = "10 дней"
                item.setText(expiry)
            self.expiry_data[row] = expiry  # Сохраняем значение в памяти

    def show_stock_context_menu(self, pos):
        # Контекстное меню для удаления строк
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить строку")
        action = menu.exec_(self.reports_table.mapToGlobal(pos))

        if action == delete_action:
            selected_rows = sorted(set(index.row() for index in self.reports_table.selectedIndexes()), reverse=True)
            for row in selected_rows:
                product = self.stock_products[row]
                # Удаляем отчет из базы, если он существует
                report = self.session.query(OtchetyPoOstatkamTovarov).filter(
                    OtchetyPoOstatkamTovarov.tovar_id == product.id,
                    OtchetyPoOstatkamTovarov.data_formirovaniya_otcheta == self.selected_stock_date_obj
                ).first()
                if report:
                    self.session.delete(report)
                self.reports_table.removeRow(row)
                # Удаляем данные о сроке годности
                if row in self.expiry_data:
                    del self.expiry_data[row]

            try:
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText(f"Ошибка при удалении отчета: {str(e)}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()

            # Обновляем нумерацию и данные о сроках годности
            new_expiry_data = {}
            for i in range(self.reports_table.rowCount()):
                self.reports_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                old_row = i + sum(1 for r in selected_rows if r <= i)  # Смещение из-за удаленных строк
                if old_row in self.expiry_data:
                    new_expiry_data[i] = self.expiry_data[old_row]
                    self.reports_table.setItem(i, 4, QTableWidgetItem(self.expiry_data[old_row]))
                else:
                    new_expiry_data[i] = "10 дней"
                    self.reports_table.setItem(i, 4, QTableWidgetItem("10 дней"))
            self.expiry_data = new_expiry_data

            # Обновляем список товаров
            remaining_products = []
            for i in range(self.reports_table.rowCount()):
                remaining_products.append(self.stock_products[i])
            self.stock_products = remaining_products
            
    def handle_tab_change(self, index):
        # Сбрасываем состояние таблицы и текущий тип отчета при переключении вкладок
        if index != self.reports_index:
            self.current_report_type = None
            self.reports_table.setRowCount(0)
            self.reports_table.setColumnCount(0)
            # Сбрасываем сохраненные даты
            if hasattr(self, 'selected_arrival_date_obj'):
                delattr(self, 'selected_arrival_date_obj')
            if hasattr(self, 'selected_stock_date_obj'):
                delattr(self, 'selected_stock_date_obj')
            if hasattr(self, 'selected_loss_date_obj'):
                delattr(self, 'selected_loss_date_obj')
            if hasattr(self, 'selected_order_date_obj'):
                delattr(self, 'selected_order_date_obj')

        if index == self.reports_index:
            # Если выбрана вкладка "Отчеты", показываем меню отчетов
            tab_rect = self.custom_tab_bar.tabRect(self.reports_index)
            menu_pos = self.custom_tab_bar.mapToGlobal(tab_rect.bottomLeft())
            self.reports_menu.exec_(menu_pos)
            print("Открыто меню отчетов при переключении на вкладку 'Отчеты'")

    def load_stock_reports(self):
        self.current_report_type = "stock"
        date_dialog = DateSelectionDialog(self)
        date_dialog.setWindowTitle("Выбор даты для отчета по остаткам")
        date_dialog.title_label.setText("Выберите дату для отчета по остаткам товаров")
        if date_dialog.exec_() == QDialog.Accepted:
            selected_qdate = date_dialog.get_selected_date()
            self.selected_stock_date_obj = selected_qdate.toPython()  # Сохраняем как datetime.date

            # Локализация для русского языка
            locale = QLocale(QLocale.Russian, QLocale.Russia)
            self.selected_stock_date = locale.toString(selected_qdate, "d MMMM yyyy") + "г"

            # Загружаем все товары из таблицы Tovar
            try:
                products = self.session.query(Tovar).all()
                if not products:
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Информация")
                    msg.setText("В базе данных нет товаров для формирования отчета.")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.button(QMessageBox.Ok).setText("Хорошо")
                    msg.exec_()
                    self.current_report_type = None
                    self.reports_table.setRowCount(0)
                    self.reports_table.setColumnCount(0)
                    return
                self.stock_products = products  # Сохраняем для использования в обработчиках
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText(f"Ошибка при загрузке товаров: {str(e)}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                self.current_report_type = None
                self.reports_table.setRowCount(0)
                self.reports_table.setColumnCount(0)
                return

            # Загружаем существующие отчеты по остаткам за выбранную дату
            try:
                reports = self.session.query(OtchetyPoOstatkamTovarov).filter(
                    OtchetyPoOstatkamTovarov.data_formirovaniya_otcheta == self.selected_stock_date_obj
                ).all()
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText(f"Ошибка при загрузке отчетов: {str(e)}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                self.current_report_type = None
                self.reports_table.setRowCount(0)
                self.reports_table.setColumnCount(0)
                return

            # Создаем словарь для быстрого поиска отчетов
            report_dict = {report.tovar_id: report for report in reports if report.tovar_id}

            # Настраиваем таблицу
            self.reports_table.setRowCount(len(products))
            self.reports_table.setColumnCount(5)
            self.reports_table.setHorizontalHeaderLabels([
                "№", "Товар", "Поставщик", "Количество товара", "Срок годности"
            ])

            # Очищаем словарь для хранения временных значений срока годности
            self.expiry_data = {}

            for row, product in enumerate(products):
                # № (порядковый номер)
                number_item = QTableWidgetItem(str(row + 1))
                number_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Нередактируемое
                self.reports_table.setItem(row, 0, number_item)

                # Товар (из Tovar.opisanie)
                opisanie = str(product.opisanie) if product.opisanie else "Описание отсутствует"
                product_item = QTableWidgetItem(opisanie)
                product_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Нередактируемое
                self.reports_table.setItem(row, 1, product_item)

                # Поставщик (из Postavshik.nazvanie_postavshika)
                supplier_name = "Не указан"
                if product.postavshik_id:
                    try:
                        supplier = self.session.query(Postavshik).filter_by(id=product.postavshik_id).first()
                        supplier_name = str(supplier.nazvanie_postavshika) if supplier else "Поставщик не найден"
                    except Exception as e:
                        supplier_name = f"Ошибка: {str(e)}"
                supplier_item = QTableWidgetItem(supplier_name)
                supplier_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Нередактируемое
                self.reports_table.setItem(row, 2, supplier_item)

                # Количество товара (всегда 0 изначально)
                quantity = "0"
                quantity_item = QTableWidgetItem(quantity)
                quantity_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)  # Редактируемое
                self.reports_table.setItem(row, 3, quantity_item)

                # Срок годности (по умолчанию "10 дней", редактируемое)
                expiry = "10 дней"
                expiry_item = QTableWidgetItem(expiry)
                expiry_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)  # Редактируемое
                self.reports_table.setItem(row, 4, expiry_item)
                self.expiry_data[row] = expiry  # Сохраняем начальное значение

            self.reports_table.resizeColumnsToContents()

            # Подключаем обработчик изменения данных
            self.reports_table.itemChanged.connect(self.update_stock_report)

            # Включаем контекстное меню для удаления строк
            self.reports_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.reports_table.customContextMenuRequested.connect(self.show_stock_context_menu)

        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Отмена")
            msg.setText("Формирование отчета по остаткам товаров отменено.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            self.current_report_type = None
            self.reports_table.setRowCount(0)
            self.reports_table.setColumnCount(0)


    def generate_general_accounting_report(self):
        """Генерирует пустой отчет 'Общий учет' в формате PDF."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"general_accounting_report_{timestamp}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            title_style.fontName = 'TimesNewRoman'
            title_style.alignment = 1
            title = "Общий учет"
            title_paragraph = Paragraph(title, title_style)
            elements.append(title_paragraph)

            normal_style = styles['Normal']
            normal_style.fontName = 'TimesNewRoman'
            normal_style.fontSize = 10
            normal_style.leading = 14

            elements.append(Paragraph("<br/>", normal_style))

            # Заголовки таблицы
            headers = ["№", "Дата", "Наименование", "Количество", "Ед. изм.", "Цена", "Сумма"]
            data = [headers]

            # Создаем пустую таблицу
            col_widths = [30, 80, 150, 50, 50, 60, 60]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'TimesNewRoman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph("Итого: -", normal_style))

            doc.build(elements)
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText(f"Отчет 'Общий учет' успешно создан: {filename}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при создании отчета 'Общий учет': {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def generate_invoice_report(self):
        """Генерирует пустой отчет 'Счет-фактура' в формате PDF."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"invoice_report_{timestamp}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            title_style.fontName = 'TimesNewRoman'
            title_style.alignment = 1
            title = "Счет-фактура"
            title_paragraph = Paragraph(title, title_style)
            elements.append(title_paragraph)

            normal_style = styles['Normal']
            normal_style.fontName = 'TimesNewRoman'
            normal_style.fontSize = 10
            normal_style.leading = 14

            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph("Поставщик: ____________________________", normal_style))
            elements.append(Paragraph("Покупатель: __________________________", normal_style))
            elements.append(Paragraph("Дата: _______________________________", normal_style))
            elements.append(Paragraph("<br/>", normal_style))

            # Заголовки таблицы
            headers = ["№", "Наименование товара", "Количество", "Цена", "Сумма", "НДС", "Сумма с НДС"]
            data = [headers]

            # Создаем пустую таблицу
            col_widths = [30, 150, 50, 60, 60, 50, 60]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'TimesNewRoman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph("Итого: -", normal_style))
            elements.append(Paragraph("Сумма НДС: -", normal_style))
            elements.append(Paragraph("Всего с НДС: -", normal_style))

            doc.build(elements)
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText(f"Отчет 'Счет-фактура' успешно создан: {filename}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при создании отчета 'Счет-фактура': {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def generate_specification_report(self):
        """Генерирует пустой отчет 'Спецификация' в формате PDF."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"specification_report_{timestamp}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            title_style.fontName = 'TimesNewRoman'
            title_style.alignment = 1
            title = "Спецификация"
            title_paragraph = Paragraph(title, title_style)
            elements.append(title_paragraph)

            normal_style = styles['Normal']
            normal_style.fontName = 'TimesNewRoman'
            normal_style.fontSize = 10
            normal_style.leading = 14

            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph("Договор №: __________________________", normal_style))
            elements.append(Paragraph("Дата: _______________________________", normal_style))
            elements.append(Paragraph("<br/>", normal_style))

            # Заголовки таблицы
            headers = ["№", "Наименование", "Ед. изм.", "Количество", "Цена за ед.", "Общая сумма"]
            data = [headers]

            # Создаем пустую таблицу
            col_widths = [30, 150, 50, 50, 60, 60]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'TimesNewRoman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph("Итого: -", normal_style))

            doc.build(elements)
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText(f"Отчет 'Спецификация' успешно создан: {filename}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при создании отчета 'Спецификация': {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def generate_pdf_report(self):
        if not self.current_report_type:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Сначала выберите тип отчета!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            return

        if self.current_report_type == "arrival":
            if not hasattr(self, 'selected_arrival_date_obj') or self.selected_arrival_date_obj is None:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText("Дата для отчета по поступлению товаров не выбрана!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                return

            # Формируем данные для PDF на основе текущего состояния таблицы
            title = f"Отчет по поступлению товаров на {self.selected_arrival_date}"
            headers = ["№", "Дата поступления", "Количество", "Товар", "Описание", "Поставщик"]
            data = [headers]

            total_quantity = 0

            for row in range(self.reports_table.rowCount()):
                number = self.reports_table.item(row, 0).text()  # №
                arrival_date = self.reports_table.item(row, 1).text()  # Дата поступления
                quantity = int(self.reports_table.item(row, 2).text())  # Количество
                product_name = self.reports_table.item(row, 3).text()  # Товар
                description = self.reports_table.item(row, 4).text()  # Описание
                supplier = self.reports_table.item(row, 5).text()  # Поставщик

                total_quantity += quantity

                data.append([
                    number,
                    arrival_date,
                    str(quantity),
                    product_name,
                    description,
                    supplier
                ])

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arrival_report_{timestamp}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            title_style.fontName = 'TimesNewRoman'
            title_style.alignment = 1
            title_paragraph = Paragraph(title, title_style)
            elements.append(title_paragraph)

            normal_style = styles['Normal']
            normal_style.fontName = 'TimesNewRoman'
            normal_style.fontSize = 10
            normal_style.leading = 14

            elements.append(Paragraph("<br/>", normal_style))

            # Создаем стиль для текста с переносом в колонках "Товар" и "Описание"
            cell_style = ParagraphStyle(
                name='CellStyle',
                fontName='TimesNewRoman',
                fontSize=8,
                leading=10,
                wordWrap='CJK',
                alignment=1
            )

            # Преобразуем данные в колонках "Товар" и "Описание" в Paragraph для переноса текста
            for row in range(1, len(data)):  # Пропускаем заголовок
                data[row][3] = Paragraph(data[row][3], cell_style)  # Товар
                data[row][4] = Paragraph(data[row][4], cell_style)  # Описание

            # Таблица с заданной шириной колонок
            col_widths = [30, 100, 50, 100, 150, 100]  # Ширина колонок в пунктах
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'TimesNewRoman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

            # Итоговое количество
            elements.append(Paragraph("<br/>", normal_style))
            elements.append(Paragraph(f"Итого поступило: {total_quantity} единиц", normal_style))

            doc.build(elements)
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText(f"Отчет успешно создан: {filename}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

        elif self.current_report_type == "stock":
                if not hasattr(self, 'selected_stock_date_obj') or self.selected_stock_date_obj is None:
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Ошибка")
                    msg.setText("Дата для отчета по остаткам товаров не выбрана!")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.button(QMessageBox.Ok).setText("Хорошо")
                    msg.exec_()
                    return

                title = f"Отчет по остаткам товаров на {self.selected_stock_date}"
                headers = ["№", "Товар", "Поставщик", "Количество товара", "Срок годности"]
                data = [headers]

                total_quantity = 0

                for row in range(self.reports_table.rowCount()):
                    number = self.reports_table.item(row, 0).text()
                    product = self.reports_table.item(row, 1).text()
                    supplier = self.reports_table.item(row, 2).text()
                    quantity = int(self.reports_table.item(row, 3).text() or 0)
                    expiry = self.reports_table.item(row, 4).text()

                    total_quantity += quantity

                    data.append([
                        number,
                        product,
                        supplier,
                        str(quantity),
                        expiry
                    ])

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"stock_report_{timestamp}.pdf"
                doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
                elements = []

                styles = getSampleStyleSheet()
                title_style = styles['Heading1']
                title_style.fontName = 'TimesNewRoman'
                title_style.alignment = 1
                title_paragraph = Paragraph(title, title_style)
                elements.append(title_paragraph)

                normal_style = styles['Normal']
                normal_style.fontName = 'TimesNewRoman'
                normal_style.fontSize = 10
                normal_style.leading = 14

                elements.append(Paragraph("<br/>", normal_style))

                cell_style = ParagraphStyle(
                    name='CellStyle',
                    fontName='TimesNewRoman',
                    fontSize=8,
                    leading=10,
                    wordWrap='CJK',
                    alignment=1
                )

                for row in range(1, len(data)):
                    data[row][1] = Paragraph(data[row][1], cell_style)  # Товар
                    data[row][2] = Paragraph(data[row][2], cell_style)  # Поставщик
                    data[row][4] = Paragraph(data[row][4], cell_style)  # Срок годности

                col_widths = [30, 150, 100, 70, 100]
                table = Table(data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'TimesNewRoman'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(table)

                elements.append(Paragraph("<br/>", normal_style))
                elements.append(Paragraph(f"Итого остаток: {total_quantity} единиц", normal_style))

                doc.build(elements)
                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText(f"Отчет успешно создан: {filename}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()

class AuthWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedSize(380, 450)
        self.setWindowIcon(QIcon("logo.png"))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(40, 40, 40, 40)

        self.greeting_label = QLabel("Привет, я букет! А ты кто?")
        self.greeting_label.setObjectName("greetingLabel")
        self.greeting_label.setWordWrap(True)
        self.layout.addWidget(self.greeting_label)

        self.login_label = QLabel("Логин:")
        self.login_label.setObjectName("inputLabel")
        self.layout.addWidget(self.login_label)
        self.login_entry = QLineEdit()
        self.login_entry.setObjectName("inputField")
        self.login_entry.setPlaceholderText("Введите логин")
        self.layout.addWidget(self.login_entry)

        self.password_label = QLabel("Пароль:")
        self.password_label.setObjectName("inputLabel")
        self.layout.addWidget(self.password_label)
        self.password_entry = QLineEdit()
        self.password_entry.setObjectName("inputField")
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.password_entry.setPlaceholderText("Введите пароль")
        self.layout.addWidget(self.password_entry)

        self.login_button = QPushButton("Войти")
        self.login_button.setObjectName("loginButton")
        self.login_button.clicked.connect(self.authenticate)
        self.layout.addWidget(self.login_button)

        self.image_label = QLabel()
        pixmap = QPixmap("fll.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(900, 50, Qt.KeepAspectRatio)
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self.image_label)
        else:
            print("Ошибка: файл 'fll.png' не найден")

        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                print("Стили для окна авторизации успешно загружены!")
                print("Первые 100 символов стилей:", stylesheet[:100])
        except FileNotFoundError:
            msg = QMessageBox(self)
            msg.setWindowTitle("Предупреждение")
            msg.setText("Файл styles.qss не найден. Стили не применены.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Ошибка при загрузке стилей: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()
            raise

    def authenticate(self):
        login = self.login_entry.text().strip()
        password = self.password_entry.text().strip()

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if login in USERS and USERS[login] == hashed_password:
            print(f"Авторизация успешна для пользователя: {login}")
            self.close()
            try:
                self.launch_main_window(login)
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка")
                msg.setText(f"Ошибка при запуске главного окна: {str(e)}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.button(QMessageBox.Ok).setText("Хорошо")
                msg.exec_()
                raise
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка")
            msg.setText("Неверный логин или пароль!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.button(QMessageBox.Ok).setText("Хорошо")
            msg.exec_()

    def launch_main_window(self, user_role):
        print("Запуск главного окна...")
        self.main_window = MainWindow(user_role)
        self.main_window.show()
        print("Главное окно отображено!")

def main():
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()