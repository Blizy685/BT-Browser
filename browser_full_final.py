# browser_full_final_v4.py
import sys, os, json
from PyQt5.QtCore import Qt, QUrl, QTimer, QDateTime, QSize
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QToolBar, QAction,
                             QLineEdit, QMenu, QWidget, QVBoxLayout, QLabel, QTextEdit,
                             QListWidget, QPushButton, QHBoxLayout, QComboBox, QCheckBox,
                             QFileDialog, QMessageBox, QDialog, QFormLayout, QCalendarWidget,
                             QInputDialog)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtGui import QIcon

# ---------------- CONFIG ----------------
DEFAULT_CONFIG = {
    "username": "Guest",
    "password": "",
    "homepage": "https://www.google.com",
    "theme": "Light",
    "squared_buttons": True,
    "show_bookmarks_tab": True,
    "show_calendar_tab": True,
    "adblock_enabled": True,
    "auto_accept_cookies": True,
    "coins": 0,
    "history": [],
    "bookmarks": [],
    "incognito": False,
    "debug_mode": False
}

ACCOUNTS_DIR = "accounts"
if not os.path.exists(ACCOUNTS_DIR):
    os.makedirs(ACCOUNTS_DIR)

def account_file(username):
    return os.path.join(ACCOUNTS_DIR, f"{username}.json")

def load_account(username):
    path = account_file(username)
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg.update(data)
        except:
            pass
    return cfg

def save_account(username, cfg):
    try:
        with open(account_file(username), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Error saving account:", e)

# ---------------- ADBLOCK ----------------
AD_DOMAINS = ["doubleclick.net", "adservice.google.com", "ads.twitter.com", "ads.facebook.com"]

class BrowserPage(QWebEnginePage):
    def __init__(self, browser_window, profile=None, incognito=False):
        super().__init__(profile, browser_window)
        self.browser_window = browser_window
        self.incognito = incognito

    def acceptNavigationRequest(self, url, nav_type, isMainFrame):
        try:
            if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
                if self.browser_window.config.get("adblock_enabled", True):
                    host = url.host().lower()
                    for ad in AD_DOMAINS:
                        if ad in host:
                            return False
                self.browser_window.award_coins(1)
                if not self.incognito:
                    self.browser_window.add_history(url.toString())
        except:
            pass
        return super().acceptNavigationRequest(url, nav_type, isMainFrame)

# ---------------- BROWSER ----------------
class Browser(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.config = load_account(username)
        self.setWindowTitle(f"BT Browser - {self.username}")
        self.resize(1200, 800)
        self.setWindowIcon(QIcon())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_change)
        self.setCentralWidget(self.tabs)

        # Toolbar & status
        self._create_toolbar()
        self._create_status_widgets()
        self.apply_styles()

        # Bookmarks, history, calendar
        self._create_history_widget()
        self._create_calendar_widget()

        # Open homepage
        self.add_new_tab(QUrl(self.config.get("homepage")), "Home")

    # ---------------- TAB METHODS ----------------
    def add_new_tab(self, qurl=None, label="New Tab"):
        if qurl is None: qurl = QUrl("https://www.google.com")
        browser = QWebEngineView()
        page = BrowserPage(self, incognito=self.config.get("incognito", False))
        browser.setPage(page)
        browser.setUrl(qurl)
        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)

        # URL bar update
        browser.urlChanged.connect(lambda url, b=browser: self.update_urlbar(url, b))
        browser.loadFinished.connect(lambda _, b=browser: self.tabs.setTabText(self.tabs.indexOf(b), b.page().title()))

        # Favicon
        browser.iconChanged.connect(lambda icon, b=browser: self.tabs.setTabIcon(self.tabs.indexOf(b), icon))
        return browser

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            w = self.tabs.widget(index)
            if isinstance(w, QWebEngineView):
                w.setUrl(QUrl(self.config.get("homepage", "https://www.google.com")))

    def on_tab_change(self, index):
        w = self.tabs.widget(index)
        if isinstance(w, QWebEngineView):
            self.update_urlbar(w.url(), w)

    # ---------------- TOOLBAR ----------------
    def _create_toolbar(self):
        self.toolbar = QToolBar("Navigation")
        self.addToolBar(self.toolbar)

        back = QAction("Back", self)
        back.triggered.connect(lambda: self.safe_do(lambda w: w.back()))
        self.toolbar.addAction(back)

        forward = QAction("Forward", self)
        forward.triggered.connect(lambda: self.safe_do(lambda w: w.forward()))
        self.toolbar.addAction(forward)

        reload = QAction("Reload", self)
        reload.triggered.connect(lambda: self.safe_do(lambda w: w.reload()))
        self.toolbar.addAction(reload)

        home = QAction("Home", self)
        home.triggered.connect(lambda: self.safe_do(lambda w: w.setUrl(QUrl(self.config.get("homepage")))))
        self.toolbar.addAction(home)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        new_tab = QAction("+ Tab", self)
        new_tab.triggered.connect(lambda: self.add_new_tab(QUrl(self.config.get("homepage")), "New Tab"))
        self.toolbar.addAction(new_tab)

        menu_btn = QAction("☰", self)
        menu_btn.triggered.connect(self.show_main_menu)
        self.toolbar.addAction(menu_btn)

    def safe_do(self, func):
        w = self.tabs.currentWidget()
        if isinstance(w, QWebEngineView):
            func(w)

    def navigate_to_url(self):
        url_text = self.url_bar.text()
        if not url_text.startswith("http"):
            url_text = "http://" + url_text
        self.safe_do(lambda w: w.setUrl(QUrl(url_text)))

    def update_urlbar(self, q, browser=None):
        if browser == self.tabs.currentWidget():
            self.url_bar.setText(q.toString())

    # ---------------- STATUS ----------------
    def _create_status_widgets(self):
        self.clock_label = QLabel()
        self.coin_label = QLabel()
        self.incognito_label = QLabel()
        self.statusBar().addPermanentWidget(self.coin_label)
        self.statusBar().addPermanentWidget(self.clock_label)
        self.statusBar().addPermanentWidget(self.incognito_label)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock_and_coins)
        self._clock_timer.start(1000)
        self._update_clock_and_coins()

    def _update_clock_and_coins(self):
        self.clock_label.setText(QDateTime.currentDateTime().toString("HH:mm:ss"))
        self.coin_label.setText(f"Coins: {self.config.get('coins',0)}")
        self.incognito_label.setText("Incognito" if self.config.get("incognito",False) else "")

    # ---------------- HISTORY ----------------
    def _create_history_widget(self):
        self.history_tab_widget = QWidget()
        layout = QVBoxLayout(self.history_tab_widget)
        self.history_list_widget = QListWidget()
        self.history_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list_widget.customContextMenuRequested.connect(self.history_context_menu)
        layout.addWidget(self.history_list_widget)
        self.update_history_list()

    def add_history(self, url):
        if self.config.get("incognito", False): return
        hist = self.config.get("history", [])
        if not hist or hist[-1] != url:
            hist.append(url)
            self.config["history"] = hist
            save_account(self.username, self.config)
            self.update_history_list()

    def update_history_list(self):
        self.history_list_widget.clear()
        for u in reversed(self.config.get("history", [])):
            self.history_list_widget.addItem(u)

    def open_history_tab(self):
        idx = self.tabs.indexOf(self.history_tab_widget)
        if idx == -1: idx = self.tabs.addTab(self.history_tab_widget, "History")
        self.tabs.setCurrentIndex(idx)

    def history_context_menu(self, pos):
        item = self.history_list_widget.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        act_open = QAction("Open in New Tab", self)
        act_open.triggered.connect(lambda: self.add_new_tab(QUrl(item.text()), item.text()))
        menu.addAction(act_open)
        act_del = QAction("Delete", self)
        act_del.triggered.connect(lambda: self.delete_history_item(item))
        menu.addAction(act_del)
        menu.exec_(self.history_list_widget.mapToGlobal(pos))

    def delete_history_item(self, item):
        url = item.text()
        hist = [h for h in self.config.get("history", []) if h != url]
        self.config["history"] = hist
        save_account(self.username, self.config)
        self.update_history_list()

    # ---------------- CALENDAR ----------------
    def _create_calendar_widget(self):
        self.calendar_tab_widget = QWidget()
        layout = QVBoxLayout(self.calendar_tab_widget)
        self.calendar = QCalendarWidget()
        layout.addWidget(self.calendar)

    def open_calendar_tab(self):
        idx = self.tabs.indexOf(self.calendar_tab_widget)
        if idx == -1: idx = self.tabs.addTab(self.calendar_tab_widget, "Calendar")
        self.tabs.setCurrentIndex(idx)

    # ---------------- COINS ----------------
    def award_coins(self, amount):
        if self.config.get("incognito", False): return
        self.config["coins"] = self.config.get("coins",0) + amount
        self._update_clock_and_coins()
        save_account(self.username, self.config)

    # ---------------- SETTINGS ----------------
    def show_settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QFormLayout(dlg)

        homepage_edit = QLineEdit(self.config.get("homepage"))
        layout.addRow("Default Home Page:", homepage_edit)

        username_edit = QLineEdit(self.config.get("username"))
        layout.addRow("Username:", username_edit)

        password_edit = QLineEdit(self.config.get("password"))
        password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Password:", password_edit)

        incognito_chk = QCheckBox()
        incognito_chk.setChecked(self.config.get("incognito", False))
        layout.addRow("Enable Incognito:", incognito_chk)

        debug_chk = QCheckBox()
        debug_chk.setChecked(self.config.get("debug_mode", False))
        layout.addRow("Debug Mode:", debug_chk)

        calendar_chk = QCheckBox()
        calendar_chk.setChecked(self.config.get("show_calendar_tab", True))
        layout.addRow("Show Calendar Tab:", calendar_chk)

        squared_btn_chk = QCheckBox()
        squared_btn_chk.setChecked(self.config.get("squared_buttons", True))
        layout.addRow("Squared Buttons:", squared_btn_chk)

        theme_combo = QComboBox()
        theme_combo.addItems(["Light","Dark","Orange Juice"])
        theme_combo.setCurrentText(self.config.get("theme","Light"))
        layout.addRow("Theme:", theme_combo)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self._save_settings(
            homepage_edit.text(), username_edit.text(), password_edit.text(),
            incognito_chk.isChecked(), debug_chk.isChecked(),
            calendar_chk.isChecked(), squared_btn_chk.isChecked(),
            theme_combo.currentText(),
            dlg
        ))
        layout.addRow(save_btn)
        dlg.exec_()

    def _save_settings(self, homepage, username, password, incognito, debug, calendar, squared, theme, dlg):
        self.config["homepage"] = homepage
        self.config["username"] = username
        self.config["password"] = password
        self.config["incognito"] = incognito
        self.config["debug_mode"] = debug
        self.config["show_calendar_tab"] = calendar
        self.config["squared_buttons"] = squared
        self.config["theme"] = theme
        save_account(self.username, self.config)
        self.apply_styles()
        dlg.accept()

    # ---------------- STYLES ----------------
    def apply_styles(self):
        theme = self.config.get("theme", "Light")
        squared = self.config.get("squared_buttons", True)

        if theme=="Light":
            bg, fg, status_fg = "#ffffff", "#000000", "#555555"
        elif theme=="Dark":
            bg, fg, status_fg = "#282c34", "#ffffff", "#aaaaaa"
        elif theme=="Orange Juice":
            bg, fg, status_fg = "#ffe4b5", "#000000", "#555555"

        border_radius = "0px" if squared else "6px"

        css = f"""
            QMainWindow {{ background-color: {bg}; color: {fg}; }}
            QToolBar {{ background-color: {bg}; spacing: 6px; }}
            QLineEdit {{ background-color: #f0f0f0; color: {fg}; border: 1px solid #888; border-radius: {border_radius}; padding: 4px; }}
            QPushButton {{ background-color: #ddd; color: {fg}; border-radius: {border_radius}; padding: 6px; }}
            QPushButton:hover {{ background-color: #bbb; }}
            QTabBar::tab {{ background: #ccc; color: {fg}; padding: 6px; border-radius: {border_radius}; }}
            QTabBar::tab:selected {{ background: #aaa; }}
            QListWidget {{ background-color: #f9f9f9; color: {fg}; }}
            QLabel {{ color: {status_fg}; }}
        """
        self.setStyleSheet(css)

    # ---------------- MAIN MENU ----------------
    def show_main_menu(self):
        menu = QMenu(self)
        menu.addAction("Settings", self.show_settings_dialog)
        menu.addAction("Open History", self.open_history_tab)
        menu.addAction("Open Calendar", self.open_calendar_tab)
        menu.addAction("About", self.show_about_dialog)
        menu.exec_(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def show_about_dialog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About BT Browser")
        dlg.setText("BT Browser v4\nMade with PyQt5\nCoins system included\nFavicon support and themes.")
        dlg.exec_()

# ---------------- MAIN ----------------
def choose_account_dialog():
    dlg = QDialog()
    dlg.setWindowTitle("Choose Account")
    dlg.resize(400,200)
    layout = QVBoxLayout(dlg)

    combo = QComboBox()
    accounts = ["Guest"] + [f[:-5] for f in os.listdir(ACCOUNTS_DIR) if f.endswith(".json")]
    combo.addItems(accounts)
    layout.addWidget(combo)

    btn_layout = QHBoxLayout()
    login_btn = QPushButton("Login"); btn_layout.addWidget(login_btn)
    create_btn = QPushButton("Create"); btn_layout.addWidget(create_btn)
    delete_btn = QPushButton("Delete"); btn_layout.addWidget(delete_btn)
    layout.addLayout(btn_layout)

    selected = {"username": None}

    def do_login():
        user = combo.currentText()
        cfg = load_account(user)
        if cfg.get("password"):
            text, ok = QInputDialog.getText(dlg,"Password Required","Enter password:", QLineEdit.Password)
            if not ok or text != cfg.get("password"):
                QMessageBox.warning(dlg,"Error","Wrong password"); return
        selected["username"] = user
        dlg.accept()

    def do_create():
        text, ok = QInputDialog.getText(dlg,"Create Account","Username:")
        if ok and text:
            if text in accounts:
                QMessageBox.warning(dlg,"Exists","Account already exists")
            else:
                cfg = DEFAULT_CONFIG.copy()
                cfg["username"] = text
                save_account(text, cfg)
                combo.addItem(text)
                QMessageBox.information(dlg,"Created","Account created")

    def do_delete():
        usr = combo.currentText()
        if usr=="Guest": QMessageBox.warning(dlg,"Error","Cannot delete Guest"); return
        reply=QMessageBox.question(dlg,"Confirm","Delete account "+usr+"?",QMessageBox.Yes|QMessageBox.No)
        if reply==QMessageBox.Yes:
            os.remove(account_file(usr))
            combo.removeItem(combo.currentIndex())
            QMessageBox.information(dlg,"Deleted","Account deleted")

    login_btn.clicked.connect(do_login)
    create_btn.clicked.connect(do_create)
    delete_btn.clicked.connect(do_delete)
    dlg.exec_()
    return selected["username"] or "Guest"

def main():
    app = QApplication(sys.argv)
    username = choose_account_dialog()
    win = Browser(username)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
