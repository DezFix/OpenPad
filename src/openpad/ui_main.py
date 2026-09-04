"""Главное окно OpenPad (PyQt6)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QSlider, QSplitter, QStatusBar,
    QTableWidget, QTableWidgetItem, QToolBar, QVBoxLayout, QWidget,
    QKeySequenceEdit,
)

from . import devices as devmod
from .audio_engine import DualOutputEngine, MicPassthrough
from .audio_loader import SUPPORTED_EXTS, load_audio
from .hotkeys import GlobalHotkeyManager
from .library import Library, default_data_path


def config_path() -> Path:
    base = default_data_path().parent
    return base / "config.json"


MIC_HELP = (
    "<b>Как вывести звук в Discord / игру / голосовой чат</b><br><br>"
    "Честно про механику: оригинальный Soundpad ставит свой драйвер "
    "<i>Soundpad Virtual Audio Device</i> — это и есть «то самое левое», "
    "просто оно встроено в установщик и подписано.<br>"
    "У open-source проекта нет бесплатного подписанного kernel-драйвера, "
    "поэтому OpenPad использует стандартный приём:<br><br>"
    "1. Установите <b>VB-Cable</b> (бесплатно, 1 минута, vb-audio.com) "
    "и перезагрузитесь.<br>"
    "2. В OpenPad выберите <b>Вирт. микрофон = CABLE Input</b>.<br>"
    "3. В Discord → Настройки → Голос → Микрофон выберите "
    "<b>CABLE Output</b>.<br>"
    "4. Включите <b>«Сквозной микрофон»</b>, чтобы друзья слышали и вас, "
    "и мемы (вход = ваш реальный микрофон).<br><br>"
    "Без кабеля всё работает из коробки — но только в ваши наушники.<br>"
    "Альтернатива без установки драйвера: <b>режим Stereo Mix</b> — "
    "см. Помощь → Режим без драйвера (Stereo Mix)."
)

STEREO_HELP = (
    "<b>Режим без драйвера: Stereo Mix (запасной вариант)</b><br><br>"
    "Это встроенная фишка Windows: <i>Stereo Mix</i> подмешивает в запись "
    "всё, что играет из динамиков. Качество и задержка хуже, чем через "
    "кабель, свой голос подмешивается через «Прослушать», возможны эхо "
    "и захват лишних системных звуков. Но <b>ничего ставить не надо</b>.<br><br>"
    "1. Откройте <b>настройки звука Windows</b> (кнопка в меню Помощь → "
    "Открыть настройки звука) → вкладка <b>Запись</b>.<br>"
    "2. ПКМ по пустому месту → <b>Показать отключённые устройства</b> → "
    "включите <b>Stereo Mix / Стерео микшер</b> (Включить).<br>"
    "3. В Discord/игре выберите микрофоном <b>Stereo Mix</b>.<br>"
    "4. В OpenPad играйте как обычно в <b>динамики</b> — звук уйдёт в чат "
    "вместе со всем системным звуком.<br>"
    "5. Чтобы друзья слышали и вас: свойства вашего микрофона → "
    "вкладка <b>Прослушать</b> → галка <b>«Прослушивать с данного "
    "устройства»</b> → воспроизводить на ваши динамики. Осторожно с "
    "громкостью — возможен свист/эхо.<br><br>"
    "Если Stereo Mix нет в списке вообще — значит, его отключил "
    "производитель аудиодрайвера (часто на ноутбуках). Тогда остаются "
    "VB-Cable или будущий свой драйвер OpenPad (см. папку driver/)."
)


class HotkeyDialog(QDialog):
    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Горячая клавиша")
        self.setFixedSize(320, 130)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Нажмите комбинацию (глобальная, работает без фокуса):"))
        self.edit = QKeySequenceEdit(self)
        if current:
            self.edit.setKeySequence(QKeySequence(current))
        lay.addWidget(self.edit)
        row = QHBoxLayout()
        clear = QPushButton("Очистить")
        clear.clicked.connect(self.edit.clear)
        row.addWidget(clear)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        row.addWidget(btns)
        lay.addLayout(row)

    def value(self) -> str:
        seq = self.edit.keySequence()
        return seq.toString() if seq else ""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenPad")
        self.resize(880, 600)
        self.setAcceptDrops(True)

        self.lib = Library()
        self.lib.load()
        self.lib.prune_missing()

        self.cfg = self._load_cfg()
        self.engine = DualOutputEngine(
            speaker_device=self.cfg.get("speaker"),
            mic_device=self.cfg.get("mic"),
            speaker_gain=float(self.cfg.get("speaker_gain", 1.0)),
            mic_gain=float(self.cfg.get("mic_gain", 0.9)),
            allow_overlap=bool(self.cfg.get("allow_overlap", False)),
            stop_on_repress=bool(self.cfg.get("stop_on_repress", True)),
        )
        self.passthrough = MicPassthrough()
        self.ghk = GlobalHotkeyManager()
        self._cache: dict[str, tuple] = {}
        self._current_cat = "Все"
        self._query = ""

        self._build_ui()
        self._refresh_devices(initial=True)
        self._refresh_categories()
        self._refresh_table()
        self._refresh_hotkeys()

        if self.cfg.get("passthrough"):
            self.chk_pass.setChecked(True)
            self._toggle_passthrough(True)

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    # -- config ---------------------------------------------------------
    def _load_cfg(self) -> dict:
        try:
            p = config_path()
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_cfg(self) -> None:
        try:
            p = config_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "speaker": self.cmb_spk.currentData(),
                "mic": self.cmb_mic.currentData(),
                "speaker_gain": self.sld_spk.value() / 100,
                "mic_gain": self.sld_mic.value() / 100,
                "allow_overlap": self.chk_overlap.isChecked(),
                "stop_on_repress": self.chk_toggle.isChecked(),
                "passthrough": self.chk_pass.isChecked(),
            }
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        except Exception:
            pass

    # -- UI --------------------------------------------------------------
    def _build_ui(self):
        # меню
        mb = self.menuBar()
        m_file = mb.addMenu("Файл")
        m_file.addAction("Добавить файлы…", self.add_files, "Ctrl+O")
        m_file.addAction("Добавить папку…", self.add_folder)
        m_file.addSeparator()
        m_file.addAction("Выход", self.close, "Ctrl+Q")

        m_edit = mb.addMenu("Правка")
        m_edit.addAction("Переименовать", self.rename_selected, "F2")
        m_edit.addAction("Горячая клавиша…", self.assign_hotkey_selected)
        m_edit.addAction("Категория…", self.change_category_selected)
        m_edit.addSeparator()
        m_edit.addAction("Удалить", self.delete_selected, "Delete")

        m_play = mb.addMenu("Воспроизведение")
        m_play.addAction("Играть / Стоп", self.toggle_selected, "Space")
        m_play.addAction("Стоп всё", self.stop_all, "Escape")
        m_play.addAction("Следующий", self.play_next, "Ctrl+Right")
        m_play.addAction("Предыдущий", self.play_prev, "Ctrl+Left")

        m_help = mb.addMenu("Помощь")
        m_help.addAction("Как вывести в микрофон…", self.show_mic_help)
        m_help.addAction("Режим без драйвера (Stereo Mix)…",
                         self.show_stereo_help)
        m_help.addAction("Открыть настройки звука Windows",
                         self.open_sound_settings)
        m_help.addAction("О проекте", self.show_about)

        # верхний тулбар
        tb = QToolBar("main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        btn_add = QPushButton("＋ Добавить")
        btn_add.clicked.connect(self.add_files)
        tb.addWidget(btn_add)
        self.btn_play = QPushButton("▶ Играть")
        self.btn_play.setCheckable(True)
        self.btn_play.clicked.connect(self.toggle_selected)
        tb.addWidget(self.btn_play)
        btn_stop = QPushButton("⏹ Стоп всё")
        btn_stop.clicked.connect(self.stop_all)
        tb.addWidget(btn_stop)
        tb.addSeparator()
        btn_prev = QPushButton("⏮")
        btn_prev.clicked.connect(self.play_prev)
        tb.addWidget(btn_prev)
        btn_next = QPushButton("⏭")
        btn_next.clicked.connect(self.play_next)
        tb.addWidget(btn_next)
        tb.addSeparator()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(220)
        self.search.textChanged.connect(self._on_search)
        tb.addWidget(self.search)

        # панель устройств
        dev = QToolBar("devices", self)
        dev.setMovable(False)
        self.addToolBar(dev)
        dev.addWidget(QLabel("Динамики:"))
        self.cmb_spk = QComboBox()
        self.cmb_spk.setMinimumWidth(150)
        self.cmb_spk.currentIndexChanged.connect(self._on_device_changed)
        dev.addWidget(self.cmb_spk)
        self.sld_spk = QSlider(Qt.Orientation.Horizontal)
        self.sld_spk.setRange(0, 100)
        self.sld_spk.setValue(int(self.engine.speaker_gain * 100))
        self.sld_spk.setFixedWidth(80)
        self.sld_spk.setToolTip("Громкость в наушники")
        self.sld_spk.valueChanged.connect(self._on_gain_changed)
        dev.addWidget(self.sld_spk)
        dev.addSeparator()
        dev.addWidget(QLabel("Вирт. микрофон:"))
        self.cmb_mic = QComboBox()
        self.cmb_mic.setMinimumWidth(150)
        self.cmb_mic.currentIndexChanged.connect(self._on_device_changed)
        dev.addWidget(self.cmb_mic)
        self.sld_mic = QSlider(Qt.Orientation.Horizontal)
        self.sld_mic.setRange(0, 100)
        self.sld_mic.setValue(int(self.engine.mic_gain * 100))
        self.sld_mic.setFixedWidth(80)
        self.sld_mic.setToolTip("Громкость в Discord/игру")
        self.sld_mic.valueChanged.connect(self._on_gain_changed)
        dev.addWidget(self.sld_mic)
        btn_dev = QPushButton("⟳")
        btn_dev.setToolTip("Обновить список устройств")
        btn_dev.clicked.connect(lambda: self._refresh_devices())
        dev.addWidget(btn_dev)
        dev.addSeparator()
        self.chk_pass = QCheckBox("Сквозной микрофон")
        self.chk_pass.setToolTip("Проброс живого микрофона в виртуальный кабель")
        self.chk_pass.toggled.connect(self._toggle_passthrough)
        dev.addWidget(self.chk_pass)

        # центр: категории + таблица
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)
        lv.addWidget(QLabel("Категории:"))
        self.cat_list = QListWidget()
        self.cat_list.itemClicked.connect(self._on_category)
        lv.addWidget(self.cat_list, 1)
        lv.addWidget(QLabel("Режимы:"))
        self.chk_overlap = QCheckBox("Оверлэп (несколько сразу)")
        self.chk_overlap.setChecked(self.engine.allow_overlap)
        self.chk_overlap.toggled.connect(self._on_mode_changed)
        lv.addWidget(self.chk_overlap)
        self.chk_toggle = QCheckBox("Стоп повторным нажатием")
        self.chk_toggle.setChecked(self.engine.stop_on_repress)
        self.chk_toggle.toggled.connect(self._on_mode_changed)
        lv.addWidget(self.chk_toggle)
        lv.addWidget(QLabel("Вывод:"))
        self.lbl_mode = QLabel("…")
        self.lbl_mode.setWordWrap(True)
        self.lbl_mode.setStyleSheet("color: #555; font-size: 11px;")
        lv.addWidget(self.lbl_mode)
        splitter.addWidget(left)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Длит.", "Хоткей", "Громк.%"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, self.table.horizontalHeader().ResizeMode.Stretch)
        for c, w in ((1, 60), (2, 110), (3, 70)):
            self.table.setColumnWidth(c, w)
        self.table.setSelectionBehavior(
            self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            self.table.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(lambda idx: self._play_row(idx.row()))
        self.table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._ctx_menu)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(1, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._update_status("Готово. Перетащите аудиофайлы в окно.")

    # -- устройства -------------------------------------------------------
    def _refresh_devices(self, initial: bool = False):
        outs = devmod.list_outputs()
        cur_spk = self.cmb_spk.currentData() if not initial else self.cfg.get("speaker")
        cur_mic = self.cmb_mic.currentData() if not initial else self.cfg.get("mic")
        self.cmb_spk.blockSignals(True)
        self.cmb_mic.blockSignals(True)
        self.cmb_spk.clear()
        self.cmb_mic.clear()
        self.cmb_spk.addItem("По умолчанию", None)
        self.cmb_mic.addItem("Выкл (только динамики)", None)
        for d in outs:
            self.cmb_spk.addItem(d.name, d.name)
            self.cmb_mic.addItem(d.name, d.name)
        # восстановить выбор
        for cmb, val in ((self.cmb_spk, cur_spk), (self.cmb_mic, cur_mic)):
            if val:
                for i in range(cmb.count()):
                    if cmb.itemData(i) == val:
                        cmb.setCurrentIndex(i)
                        break
        # авто-подсказка кабеля + stereo mix
        cables = devmod.find_virtual_cables()
        self._cable_hint = cables[0].name if cables else None
        stereo = devmod.find_stereo_mix()
        self._stereo_hint = stereo[0].name if stereo else None
        self.cmb_spk.blockSignals(False)
        self.cmb_mic.blockSignals(False)
        self._on_device_changed()
        self._update_mode_label()
        if self._cable_hint:
            cables_txt = f"Найден кабель: {self._cable_hint}"
        elif self._stereo_hint:
            cables_txt = (f"Stereo Mix найден ({self._stereo_hint}) — можно "
                          f"без драйвера, см. Помощь → Stereo Mix")
        else:
            cables_txt = ("Кабель не найден, Stereo Mix не виден — играем "
                          "только в динамики (см. Помощь)")
        self._update_status(cables_txt)
        if self._cable_hint and self.cmb_mic.currentData() is None and not initial:
            self.status.showMessage(
                f"Подсказка: выберите Вирт. микрофон = {self._cable_hint} "
                f"(см. Помощь → Как вывести в микрофон)")

    def _update_mode_label(self):
        if not hasattr(self, "lbl_mode"):
            return
        if self.cmb_mic.currentData():
            self.lbl_mode.setText(
                f"🎤 Кабель: {self.cmb_mic.currentData()}")
        elif getattr(self, "_cable_hint", None):
            self.lbl_mode.setText(
                f"💡 Есть кабель: {self._cable_hint} — выбери его сверху")
        elif getattr(self, "_stereo_hint", None):
            self.lbl_mode.setText(
                f"🔊 Stereo Mix: {self._stereo_hint} — режим без драйвера")
        else:
            self.lbl_mode.setText(
                "🔈 Только динамики. Для чата нужен кабель или Stereo Mix")

    def _on_device_changed(self):
        self.engine.speaker_device = self.cmb_spk.currentData()
        self.engine.mic_device = self.cmb_mic.currentData()
        self._update_mode_label()
        self._save_cfg()

    def _on_gain_changed(self):
        self.engine.speaker_gain = self.sld_spk.value() / 100
        self.engine.mic_gain = self.sld_mic.value() / 100
        self._save_cfg()

    def _on_mode_changed(self):
        self.engine.allow_overlap = self.chk_overlap.isChecked()
        self.engine.stop_on_repress = self.chk_toggle.isChecked()
        self._save_cfg()

    def _toggle_passthrough(self, on: bool):
        if not on:
            self.passthrough.stop()
            self._save_cfg()
            return
        if self.cmb_mic.currentData() is None:
            QMessageBox.information(
                self, "Сквозной микрофон",
                "Сначала выберите «Вирт. микрофон» (например CABLE Input).")
            self.chk_pass.blockSignals(True)
            self.chk_pass.setChecked(False)
            self.chk_pass.blockSignals(False)
            return
        ok = self.passthrough.start(
            input_device=None,  # микрофон по умолчанию
            output_device=self.cmb_mic.currentData(), gain=1.0)
        if not ok:
            QMessageBox.warning(self, "Сквозной микрофон",
                                f"Не запустился: {self.passthrough.error}")
            self.chk_pass.blockSignals(True)
            self.chk_pass.setChecked(False)
            self.chk_pass.blockSignals(False)
        self._save_cfg()

    # -- категории/таблица -------------------------------------------------
    def _visible(self):
        return self.lib.search(self._query,
                               None if self._current_cat == "Все" else self._current_cat)

    def _refresh_categories(self):
        self.cat_list.clear()
        self.cat_list.addItem("Все")
        for c in self.lib.categories:
            self.cat_list.addItem(c)
        # подсветить текущую
        items = self.cat_list.findItems(self._current_cat, Qt.MatchFlag.MatchExactly)
        if items:
            self.cat_list.setCurrentItem(items[0])

    def _refresh_table(self):
        rows = self._visible()
        self._rows = rows
        self.table.setRowCount(0)
        for t in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, val in enumerate(
                    [t.name, t.duration, t.hotkey or "—", str(t.volume)]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, t.id)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
        self.setWindowTitle(f"OpenPad ({len(self.lib.tracks)} звуков)")

    def _on_search(self, text: str):
        self._query = text
        self._refresh_table()

    def _on_category(self, item):
        self._current_cat = item.text()
        self._refresh_table()

    def _selected_ids(self) -> list[str]:
        return list({self.table.item(self.table.row(i), 0)
                     .data(Qt.ItemDataRole.UserRole)
                     for i in self.table.selectedItems()
                     if self.table.item(self.table.row(i), 0)})

    def _row_track(self, row: int):
        if 0 <= row < len(getattr(self, "_rows", [])):
            return self._rows[row]
        return None

    # -- добавление ----------------------------------------------------------
    def add_files(self):
        ext = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Добавить звуки", "", f"Аудио ({ext})")
        if paths:
            n = self.lib.add_paths(paths, category=self._current_cat
                                   if self._current_cat != "Все" else "Основная")
            self._after_library_change(f"Добавлено: {n}")

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Добавить папку")
        if folder:
            n = self.lib.add_folder(folder)
            self._after_library_change(f"Добавлено: {n}")

    def _after_library_change(self, msg: str = ""):
        self.lib.save()
        self._refresh_categories()
        self._refresh_table()
        self._refresh_hotkeys()
        if msg:
            self._update_status(msg)

    # -- playback ------------------------------------------------------------
    def _audio(self, track_id: str):
        if track_id in self._cache:
            return self._cache[track_id]
        t = self.lib.by_id(track_id)
        if not t:
            return None
        try:
            data = load_audio(t.path)
        except Exception as e:
            self._update_status(f"Не играет {t.name}: {e}")
            return None
        self._cache[track_id] = data
        if len(self._cache) > 30:
            self._cache.pop(next(iter(self._cache)))
        return data

    def _play_track(self, track_id: str):
        t = self.lib.by_id(track_id)
        if not t:
            return
        audio = self._audio(track_id)
        if audio is None:
            return
        samples, sr = audio
        res = self.engine.play(track_id, samples, sr, volume=t.volume / 100)
        if res == "started":
            self._update_status(f"▶ {t.name} → динамики"
                                + (" + микрофон" if self.engine.mic_device else ""))
        else:
            self._update_status(f"⏹ {t.name}")
        self.btn_play.setChecked(self.engine.any_playing())

    def _play_row(self, row: int):
        t = self._row_track(row)
        if t:
            self.table.selectRow(row)
            self._play_track(t.id)

    def toggle_selected(self):
        rows = sorted({self.table.row(i) for i in self.table.selectedItems()})
        if self.engine.any_playing():
            # если что-то играет — стоп только если выбранное играет, иначе играть выбранное
            if rows:
                t = self._row_track(rows[0])
                if t and self.engine.is_playing(t.id):
                    self.engine.stop_all()
                    self.btn_play.setChecked(False)
                    self._update_status("Стоп")
                    return
            else:
                self.engine.stop_all()
                self.btn_play.setChecked(False)
                return
        if rows:
            self._play_row(rows[0])
        elif self._rows:
            self._play_row(0)

    def stop_all(self):
        self.engine.stop_all()
        self.btn_play.setChecked(False)
        self._update_status("Стоп")

    def play_next(self):
        if not self._rows:
            return
        rows = sorted({self.table.row(i) for i in self.table.selectedItems()})
        nxt = ((rows[0] + 1) % len(self._rows)) if rows else 0
        self._play_row(nxt)

    def play_prev(self):
        if not self._rows:
            return
        rows = sorted({self.table.row(i) for i in self.table.selectedItems()})
        prv = ((rows[0] - 1) % len(self._rows)) if rows else 0
        self._play_row(prv)

    def _poll(self):
        self.engine.cleanup()
        playing = self.engine.any_playing()
        self.btn_play.setChecked(playing)
        # подсветка
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if not item:
                continue
            tid = item.data(Qt.ItemDataRole.UserRole)
            on = self.engine.is_playing(tid)
            for c in range(4):
                it = self.table.item(r, c)
                if not it:
                    continue
                if on:
                    it.setBackground(QColor("#1a6ab5"))
                    it.setForeground(QColor("white"))
                else:
                    it.setBackground(QColor())
                    it.setForeground(QColor())

    # -- правки ---------------------------------------------------------------
    def rename_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        t = self.lib.by_id(ids[0])
        name, ok = QInputDialog.getText(self, "Переименовать", "Название:",
                                        text=t.name if t else "")
        if ok and self.lib.rename(ids[0], name):
            self._after_library_change()

    def assign_hotkey_selected(self):
        ids = self._selected_ids()
        if not ids:
            self._update_status("Выберите звук")
            return
        t = self.lib.by_id(ids[0])
        dlg = HotkeyDialog(t.hotkey if t else "", self)
        if dlg.exec():
            self.lib.set_hotkey(ids[0], dlg.value())
            self._after_library_change("Хоткей сохранён (глобальный)")

    def change_category_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        t = self.lib.by_id(ids[0])
        name, ok = QInputDialog.getText(
            self, "Категория", "Категория:",
            text=t.category if t else "Основная")
        if ok and name.strip():
            for tid in ids:
                self.lib.set_category(tid, name)
            self._after_library_change()

    def delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        self.engine.stop_all()
        for tid in ids:
            self._cache.pop(tid, None)
        n = self.lib.remove_ids(ids)
        self._after_library_change(f"Удалено: {n}")

    def _ctx_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        rows = sorted({self.table.row(i) for i in self.table.selectedItems()})
        if rows:
            menu.addAction("▶ Играть", lambda: self._play_row(rows[0]))
            menu.addSeparator()
            menu.addAction("Переименовать", self.rename_selected)
            menu.addAction("Горячая клавиша…", self.assign_hotkey_selected)
            menu.addAction("Категория…", self.change_category_selected)
            vol = menu.addMenu("Громкость")
            for v in (25, 50, 75, 100):
                vol.addAction(f"{v}%", lambda vv=v: self._set_vol_selected(vv))
            menu.addSeparator()
            menu.addAction("Удалить", self.delete_selected)
        else:
            menu.addAction("Добавить файлы…", self.add_files)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _set_vol_selected(self, v: int):
        for tid in self._selected_ids():
            self.lib.set_volume(tid, v)
        self._after_library_change()

    # -- хоткеи ------------------------------------------------------------------
    def _refresh_hotkeys(self):
        mapping = {}
        for qt_hotkey, tid in self.lib.hotkey_map().items():
            mapping[qt_hotkey] = (lambda tid=tid: self._play_track(tid))
        if mapping and GlobalHotkeyManager.available():
            ok, errs = self.ghk.refresh(mapping)
            if errs:
                self._update_status("; ".join(errs[:2]))
        else:
            self.ghk.stop()

    # -- drag&drop ------------------------------------------------------------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files: list[str] = []
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                for root, _, fns in os.walk(p):
                    for fn in fns:
                        if Path(fn).suffix.lower() in SUPPORTED_EXTS:
                            files.append(str(Path(root) / fn))
            elif p.suffix.lower() in SUPPORTED_EXTS:
                files.append(str(p))
        if files:
            n = self.lib.add_paths(files)
            self._after_library_change(f"Добавлено перетаскиванием: {n}")
        e.acceptProposedAction()

    # -- misc ------------------------------------------------------------------
    def _update_status(self, msg: str):
        self.status.showMessage(msg)

    def show_mic_help(self):
        QMessageBox.information(self, "Вывод в микрофон", MIC_HELP)

    def show_stereo_help(self):
        box = QMessageBox(self)
        box.setWindowTitle("Режим без драйвера")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(STEREO_HELP)
        btn_sound = box.addButton("Открыть настройки звука",
                                  QMessageBox.ButtonRole.ActionRole)
        box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is btn_sound:
            self.open_sound_settings()

    def open_sound_settings(self):
        if not devmod.open_sound_control_panel("recording"):
            self._update_status("Не смог открыть mmsys.cpl")

    def show_about(self):
        QMessageBox.about(
            self, "OpenPad",
            "<b>OpenPad</b> — открытый саундборд.<br>"
            "Рабочее название, v0.1.<br><br>"
            "Динамики из коробки; в чат — через VB-Cable, "
            "запасной вариант — Stereo Mix; "
            "свой драйвер — в разработке (см. папку driver/).")

    def closeEvent(self, e):
        try:
            self.engine.stop_all()
            self.ghk.stop()
            self.passthrough.stop()
            self.lib.save()
            self._save_cfg()
        finally:
            super().closeEvent(e)


def create_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("OpenPad")
    app.setStyle("Fusion")
    return app
