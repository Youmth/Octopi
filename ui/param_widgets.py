import json
import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

SLIDER_STEPS = 1000

# Unit -> factor to SI. EVERY value stored in the app (the dicts you pass to
# the panels, what core/ receives, what is saved to disk) is in SI base units
# (meters). Units only exist on screen, so mixed units can never reach the
# reconstruction code.
LENGTH_UNITS = {"nm": 1e-9, "µm": 1e-6, "mm": 1e-3, "m": 1.0}
DEFAULT_LENGTH_UNIT = "µm"


@dataclass(frozen=True)
class ParamSpec:
    """Description of one numeric parameter. All numbers are in SI units."""
    label: str
    default: float
    quantity: str = "none"      # "length" -> follows the panel's length unit; "none" -> dimensionless
    tooltip: str = ""
    positive: bool = False      # reject zero and negative values
    minimum: float | None = None  # slider range (minimum must be > 0 if log=True)
    maximum: float | None = None
    log: bool = False           # slider moves on a log scale
    searchable: bool = False    # gets min/max rows in the LimitsPanel

    def slider_range(self) -> tuple[float, float, bool]:
        if self.minimum is not None and self.maximum is not None:
            return self.minimum, self.maximum, self.log
        if self.default > 0:
            return self.default / 10, self.default * 10, True
        return -1.0, 1.0, False


class ValuePanel(QWidget):
    """Base panel: a form of rows [ entry | slider | reset ] built from a
    {key: ParamSpec} table, plus a length-unit selector and Save / Load buttons.

    * Values live in the dict you pass in (`values`), always in SI units. The
      panel writes a key there each time the user commits an entry, moves a
      slider, presses reset or loads a file. Missing keys get the spec default.
    * One length unit for the whole panel: every spec with quantity="length"
      is shown in it. Two panels can be kept in sync by connecting
      `unit_changed` to each other's `set_length_unit`.
    * `show_only(keys)` shows just those rows. Hidden rows keep their value.
    * Entries accept scientific notation and always use '.' as the decimal
      separator. A typed value outside the slider range is accepted; the
      slider just sits at the nearest end.
    """

    changed = Signal(str, float)  # key, new value (SI)
    unit_changed = Signal(str)    # new length unit

    kind = "values"  # written into saved files, checked when loading

    def __init__(self, specs: dict[str, ParamSpec], values: dict,
                 length_unit: str = DEFAULT_LENGTH_UNIT):
        super().__init__()
        self.specs = specs
        self.values = values
        self.length_unit = length_unit
        self._fields: dict[str, QLineEdit] = {}
        self._sliders: dict[str, QSlider] = {}
        self._resets: dict[str, QToolButton] = {}
        self._labels: dict[str, QLabel] = {}
        self._rows: dict[str, QWidget] = {}
        self._ranges: dict[str, tuple[float, float, bool]] = {}

        outer = QVBoxLayout(self)

        # ---- panel-wide length unit ----
        self._unit_row = QWidget()
        unit_layout = QHBoxLayout(self._unit_row)
        unit_layout.setContentsMargins(0, 0, 0, 0)
        unit_layout.addWidget(QLabel("Length unit"))
        self._unit_box = QComboBox()
        self._unit_box.addItems(list(LENGTH_UNITS))
        self._unit_box.setCurrentText(length_unit)
        self._unit_box.currentTextChanged.connect(self.set_length_unit)
        unit_layout.addWidget(self._unit_box)
        unit_layout.addStretch()
        outer.addWidget(self._unit_row)
        if not any(s.quantity == "length" for s in specs.values()):
            self._unit_row.hide()

        # ---- rows ----
        form_widget = QWidget()
        self._form = QFormLayout(form_widget)
        self._form.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(form_widget)
        for key, spec in specs.items():
            self._add_row(key, spec)

        # ---- save / load ----
        buttons = QHBoxLayout()
        save_button = QPushButton("Save...")
        save_button.setToolTip("Save these values to a JSON text file")
        save_button.clicked.connect(self.save_to_file)
        load_button = QPushButton("Load...")
        load_button.setToolTip("Load values from a file saved with Save")
        load_button.clicked.connect(self.load_from_file)
        buttons.addWidget(save_button)
        buttons.addWidget(load_button)
        buttons.addStretch()
        outer.addLayout(buttons)
        outer.addStretch()

    # ---- building ----------------------------------------------------
    def _add_row(self, key: str, spec: ParamSpec):
        if self.values.get(key) is None:
            self.values[key] = spec.default
        self._ranges[key] = spec.slider_range()

        validator = QDoubleValidator(self)
        validator.setNotation(QDoubleValidator.ScientificNotation)
        validator.setLocale(QLocale.c())

        edit = QLineEdit(self._fmt(self.values[key] / self._factor(key)))
        edit.setValidator(validator)
        edit.setToolTip(spec.tooltip)
        edit.setFixedWidth(90)
        edit.editingFinished.connect(lambda k=key: self._commit(k))
        self._fields[key] = edit

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, SLIDER_STEPS)
        slider.setValue(self._value_to_pos(key, self.values[key]))
        slider.setToolTip(spec.tooltip)
        slider.valueChanged.connect(lambda pos, k=key: self._on_slider(k, pos))
        self._sliders[key] = slider

        reset = QToolButton()
        reset.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        reset.setToolTip(self._reset_tip(key))
        reset.setAutoRaise(True)
        reset.setFocusPolicy(Qt.NoFocus)
        reset.clicked.connect(lambda _=False, k=key: self._reset(k))
        self._resets[key] = reset

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(edit)
        row_layout.addWidget(slider, 1)
        row_layout.addWidget(reset)
        self._rows[key] = row

        label = QLabel(self._label_text(key))
        self._labels[key] = label
        self._form.addRow(label, row)

    # ---- units and formatting ---------------------------------------
    @staticmethod
    def _fmt(value: float) -> str:
        return f"{value:.10g}"

    def _factor(self, key: str) -> float:
        """Display unit -> SI for this row."""
        if self.specs[key].quantity == "length":
            return LENGTH_UNITS[self.length_unit]
        return 1.0

    def _unit_text(self, key: str) -> str:
        return self.length_unit if self.specs[key].quantity == "length" else ""

    def _label_text(self, key: str) -> str:
        unit = self._unit_text(key)
        label = self.specs[key].label
        return f"{label} ({unit})" if unit else label

    def _describe(self, key: str, si_value: float) -> str:
        text = self._fmt(si_value / self._factor(key))
        unit = self._unit_text(key)
        return f"{text} {unit}" if unit else text

    def _reset_tip(self, key: str) -> str:
        return f"Reset to default ({self._describe(key, self.specs[key].default)})"

    def describe(self, key: str, si_value: float | None = None) -> str:
        """A value as text in the displayed unit, e.g. '6.8 mm'. Defaults to the
        current value; pass `si_value` to format a snapshot taken earlier."""
        return self._describe(key, self.values[key] if si_value is None else si_value)

    def set_length_unit(self, unit: str):
        if unit == self.length_unit or unit not in LENGTH_UNITS:
            return
        self.length_unit = unit
        self._unit_box.setCurrentText(unit)  # no-op if the box already shows it
        for key in self.specs:
            self._fields[key].setText(self._fmt(self.values[key] / self._factor(key)))
            self._labels[key].setText(self._label_text(key))
            self._resets[key].setToolTip(self._reset_tip(key))
        self.unit_changed.emit(unit)

    # ---- slider mapping ---------------------------------------------
    def _value_to_pos(self, key: str, value: float) -> int:
        lo, hi, log = self._ranges[key]
        if hi <= lo:
            return 0
        if log:
            value = max(value, lo)  # log of <= 0 is undefined
            frac = (math.log(value) - math.log(lo)) / (math.log(hi) - math.log(lo))
        else:
            frac = (value - lo) / (hi - lo)
        return round(min(max(frac, 0.0), 1.0) * SLIDER_STEPS)

    def _pos_to_value(self, key: str, pos: int) -> float:
        lo, hi, log = self._ranges[key]
        if hi <= lo:
            return lo
        frac = pos / SLIDER_STEPS
        if log:
            return math.exp(math.log(lo) + frac * (math.log(hi) - math.log(lo)))
        return lo + frac * (hi - lo)

    # ---- the one place that changes a value --------------------------
    def _set_value(self, key: str, si_value: float):
        factor = self._factor(key)
        shown = float(self._fmt(si_value / factor))
        # 12 digits: keeps 532e-9 == 532e-9 instead of 5.320000000000001e-07
        si_value = float(f"{shown * factor:.12g}")
        self._fields[key].setText(self._fmt(shown))
        self._sync_slider(key, si_value)

        if si_value != self.values[key]:
            self.values[key] = si_value
            self.changed.emit(key, si_value)
            self._after_change(key, si_value)

    def _sync_slider(self, key: str, si_value: float | None = None):
        if si_value is None:
            si_value = self.values[key]
        slider = self._sliders[key]
        slider.blockSignals(True)  # don't bounce back into _on_slider
        slider.setValue(self._value_to_pos(key, si_value))
        slider.blockSignals(False)

    def set_slider_range(self, key: str, lo: float, hi: float):
        """Change what the slider of `key` spans (SI units). The value itself is
        untouched, so a typed value outside the range is still kept."""
        log = self.specs[key].log and lo > 0  # a log scale needs lo > 0
        self._ranges[key] = (lo, hi, log)
        self._sync_slider(key)

    def _after_change(self, key: str, si_value: float):
        """Hook for subclasses that keep constraints between values."""

    # ---- slots ---------------------------------------------------------
    def _commit(self, key: str):
        edit, spec = self._fields[key], self.specs[key]
        shown, ok = QLocale.c().toDouble(edit.text())
        si_value = shown * self._factor(key)
        if not ok or (spec.positive and si_value <= 0):
            edit.setText(self._fmt(self.values[key] / self._factor(key)))  # revert
            return
        self._set_value(key, si_value)

    def _on_slider(self, key: str, pos: int):
        self._set_value(key, self._pos_to_value(key, pos))

    def _reset(self, key: str):
        self._set_value(key, self.specs[key].default)

    def show_only(self, keys):
        keys = set(keys)
        for key, row in self._rows.items():
            self._form.setRowVisible(row, key in keys)

    # ---- save / load -----------------------------------------------------
    def save_to_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, f"Save {self.kind}", f"{self.kind}.json", "JSON files (*.json)"
        )
        if not path:
            return
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix(".json")
        data = {
            "kind": self.kind,
            "unit_system": "SI (lengths in meters)",
            "values": {key: self.values[key] for key in self.specs},
            # For humans only, ignored when loading
            "readable": {key: self.describe(key) for key in self.specs},
        }
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, "Save failed", str(error))

    def load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Load {self.kind}", "", "JSON files (*.json);;All files (*)"
        )
        if path:
            self.load_values(Path(path))

    def load_values(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            values = data["values"]
            if not isinstance(values, dict):
                raise ValueError("'values' must be an object")
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.warning(self, "Load failed", f"Could not read {path.name}:\n{error}")
            return
        if data.get("kind") != self.kind:
            QMessageBox.warning(
                self, "Load failed",
                f"{path.name} holds '{data.get('kind')}', but this panel needs '{self.kind}'.",
            )
            return

        skipped = []
        for key, value in values.items():
            spec = self.specs.get(key)
            valid = (
                spec is not None
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and not (spec.positive and value <= 0)
            )
            if valid:
                self._set_value(key, float(value))
            else:
                skipped.append(key)
        if skipped:
            QMessageBox.information(
                self, "Load finished",
                "Skipped unknown or invalid entries:\n" + ", ".join(skipped),
            )


class ParametersPanel(ValuePanel):
    """The reconstruction parameters (wavelength, pixel pitch, distances...)."""
    kind = "parameters"

    def follow_limits(self, limits: "LimitsPanel"):
        """Make the slider of every searchable parameter span the [min, max]
        chosen in `limits`. The limits panel keeps the full (hard) range."""
        self._limits = limits
        limits.changed.connect(self._on_limit_changed)
        for key in self.specs:
            self._apply_limits(key)

    def _on_limit_changed(self, limit_key: str, _value: float):
        self._apply_limits(limit_key.rsplit("_", 1)[0])

    def _apply_limits(self, key: str):
        if key not in self.specs:
            return
        lo = self._limits.values.get(f"{key}_min")
        hi = self._limits.values.get(f"{key}_max")
        if lo is not None and hi is not None:
            self.set_slider_range(key, lo, hi)


class LimitsPanel(ValuePanel):
    """Search limits: a min row and a max row for every spec marked
    `searchable`. Stored as '<key>_min' / '<key>_max' in `values`, in SI units.
    The default limits are the slider range of each parameter, and min is
    never allowed above max (moving one drags the other along).

    Pass the SAME specs table as the ParametersPanel.
    """
    kind = "limits"

    def __init__(self, specs: dict[str, ParamSpec], values: dict,
                 length_unit: str = DEFAULT_LENGTH_UNIT):
        super().__init__(self._limit_specs(specs), values, length_unit)

    @staticmethod
    def _limit_specs(specs: dict[str, ParamSpec]) -> dict[str, ParamSpec]:
        limit_specs = {}
        for key, spec in specs.items():
            if not spec.searchable:
                continue
            lo, hi, log = spec.slider_range()
            common = dict(quantity=spec.quantity, positive=spec.positive,
                          minimum=lo, maximum=hi, log=log)
            limit_specs[f"{key}_min"] = ParamSpec(
                f"{spec.label} min", lo, tooltip=f"Lower search limit. {spec.tooltip}", **common)
            limit_specs[f"{key}_max"] = ParamSpec(
                f"{spec.label} max", hi, tooltip=f"Upper search limit. {spec.tooltip}", **common)
        return limit_specs

    def show_only(self, keys):
        """`keys` are PARAMETER keys; their min and max rows are shown."""
        super().show_only({f"{k}{suffix}" for k in keys for suffix in ("_min", "_max")})

    def _after_change(self, key: str, si_value: float):
        if key.endswith("_min"):
            other = key[:-4] + "_max"
            if si_value > self.values[other]:
                self._set_value(other, si_value)
        elif key.endswith("_max"):
            other = key[:-4] + "_min"
            if si_value < self.values[other]:
                self._set_value(other, si_value)


class FiltersPanel(ValuePanel):
    """Display filters (high-pass, low-pass, contrast, brightness)."""
    kind = "filters"