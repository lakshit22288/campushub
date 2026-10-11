import ipaddress
import math
import re
from decimal import Decimal, DivisionByZero, InvalidOperation

from django import forms
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

TOOL_TITLES = {
    "percentage": "Percentage Calculator",
    "cgpa": "CGPA Calculator",
    "units": "Unit Converter",
    "python": "Python Basics Practice",
    "sql": "SQL Query Practice",
    "linux": "Linux Command Helper",
    "subnet": "IPv4 Subnet Calculator",
    "ohms-law": "Ohm's Law Calculator",
    "power": "Power Calculator",
    "logic-gates": "Logic Gate Helper",
    "mechanical-units": "Mechanical Unit Converter",
    "area-volume": "Area & Volume Calculator",
    "mlt-dilution": "Solution Dilution Calculator",
}

UNIT_GROUPS = {
    "length": {
        "Metres (m)": Decimal("1"),
        "Kilometres (km)": Decimal("1000"),
        "Centimetres (cm)": Decimal("0.01"),
        "Millimetres (mm)": Decimal("0.001"),
        "Feet (ft)": Decimal("0.3048"),
        "Inches (in)": Decimal("0.0254"),
    },
    "mass": {
        "Kilograms (kg)": Decimal("1"),
        "Grams (g)": Decimal("0.001"),
        "Tonnes (t)": Decimal("1000"),
        "Pounds (lb)": Decimal("0.45359237"),
    },
    "temperature": {
        "Celsius (°C)": "C",
        "Fahrenheit (°F)": "F",
        "Kelvin (K)": "K",
    },
    "pressure": {
        "Pascal (Pa)": Decimal("1"),
        "Kilopascal (kPa)": Decimal("1000"),
        "Megapascal (MPa)": Decimal("1000000"),
        "Bar": Decimal("100000"),
        "Pounds per square inch (psi)": Decimal("6894.757293"),
    },
    "force": {
        "Newton": Decimal("1"),
        "Kilonewton (kN)": Decimal("1000"),
        "Pound-force (lbf)": Decimal("4.448221615"),
    },
    "torque": {
        "Newton-metre (N·m)": Decimal("1"),
        "Kilonewton-metre (kN·m)": Decimal("1000"),
        "Pound-foot (lbf·ft)": Decimal("1.355817948"),
    },
    "power": {
        "Watt": Decimal("1"),
        "Kilowatt (kW)": Decimal("1000"),
        "Horsepower (hp)": Decimal("745.699872"),
    },
    "speed": {
        "Metres per second (m/s)": Decimal("1"),
        "Kilometres per hour (km/h)": Decimal("0.2777777778"),
        "Feet per second (ft/s)": Decimal("0.3048"),
    },
}

PYTHON_EXERCISES = (
    {
        "prompt": "What does this print?  x = 3; print(x * 2)",
        "options": ("6", "33", "Error"),
        "answer": "6",
        "explanation": "The integer value 3 is multiplied by 2.",
    },
    {
        "prompt": "Which values are produced by range(3)?",
        "options": ("1, 2, 3", "0, 1, 2", "0, 1, 2, 3"),
        "answer": "0, 1, 2",
        "explanation": "range(3) starts at zero and stops before three.",
    },
    {
        "prompt": 'What does "campus".upper() return?',
        "options": ("campus", "CAMPUS", "Campus"),
        "answer": "CAMPUS",
        "explanation": "upper() returns a copy of the string in uppercase.",
    },
)

SQL_EXAMPLES = {
    "select": "SELECT name, branch FROM students WHERE semester = 4 ORDER BY name;",
    "join": (
        "SELECT students.name, branches.name AS branch\n"
        "FROM students\n"
        "JOIN branches ON students.branch_id = branches.id;"
    ),
    "aggregate": (
        "SELECT branch_id, COUNT(*) AS student_count\n"
        "FROM students\n"
        "GROUP BY branch_id;"
    ),
}

LINUX_COMMANDS = (
    ("ls", "List files"),
    ("cd", "Change directory"),
    ("pwd", "Show current directory"),
    ("mkdir", "Create directory"),
    ("cp", "Copy files"),
    ("mv", "Move or rename files"),
    ("rm", "Remove files"),
    ("grep", "Search text"),
)


class BoundedDecimalField(forms.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 20)
        kwargs.setdefault("decimal_places", 6)
        super().__init__(*args, **kwargs)


class NumberInputForm(forms.Form):
    a = BoundedDecimalField(label="A", min_value=0)
    b = BoundedDecimalField(label="B", min_value=0)


class CgpaForm(forms.Form):
    grades = forms.CharField(
        label="Semester or subject GPAs (comma-separated)",
        initial="8,7.5,9,8.2",
        max_length=300,
        widget=forms.TextInput(attrs={"placeholder": "8, 7.5, 9"}),
    )

    def clean_grades(self):
        grades = []
        for value in self.cleaned_data["grades"].split(","):
            try:
                grade = Decimal(value.strip())
            except InvalidOperation as error:
                raise forms.ValidationError("Each GPA must be a valid number.") from error
            if not grade.is_finite() or grade < 0 or grade > 10:
                raise forms.ValidationError("Each GPA must be between 0 and 10.")
            grades.append(grade)
        if not grades or len(grades) > 30:
            raise forms.ValidationError("Enter between 1 and 30 GPA values.")
        return grades


class TwoNumbersForm(forms.Form):
    first = BoundedDecimalField(label="Voltage (V)", min_value=0)
    second = BoundedDecimalField(label="Current (A)", min_value=0)


class OhmForm(forms.Form):
    voltage = BoundedDecimalField(label="Voltage (V)", min_value=0, required=False)
    current = BoundedDecimalField(label="Current (A)", min_value=0, required=False)
    resistance = BoundedDecimalField(label="Resistance (Ω)", min_value=0, required=False)

    def clean(self):
        cleaned = super().clean()
        values = [cleaned.get("voltage"), cleaned.get("current"), cleaned.get("resistance")]
        if sum(value is not None for value in values) != 2:
            raise forms.ValidationError("Enter exactly two values: voltage, current, or resistance.")
        if cleaned.get("resistance") == 0:
            raise forms.ValidationError("Resistance cannot be zero.")
        return cleaned


class SubnetForm(forms.Form):
    address = forms.GenericIPAddressField(
        label="IPv4 address",
        protocol="IPv4",
        initial="192.168.1.10",
    )
    prefix = forms.IntegerField(label="CIDR prefix", min_value=0, max_value=32, initial=24)


class UnitForm(forms.Form):
    category = forms.ChoiceField(label="Quantity")
    value = BoundedDecimalField(label="Value", initial=1)
    from_unit = forms.ChoiceField(label="From")
    to_unit = forms.ChoiceField(label="To")

    def __init__(self, *args, mechanical=False, **kwargs):
        super().__init__(*args, **kwargs)
        groups = ("pressure", "force", "torque", "power", "speed") if mechanical else (
            "length", "mass", "temperature"
        )
        self.groups = groups
        self.fields["category"].choices = [(group, group.title()) for group in groups]
        selected = self.data.get("category") or self.initial.get("category") or groups[0]
        self._set_units(selected if selected in groups else groups[0])

    def _set_units(self, category):
        units = list(UNIT_GROUPS[category])
        self.fields["from_unit"].choices = [(unit, unit) for unit in units]
        self.fields["to_unit"].choices = [(unit, unit) for unit in units]
        self.fields["from_unit"].initial = units[0]
        self.fields["to_unit"].initial = units[1]

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category in UNIT_GROUPS:
            valid = set(UNIT_GROUPS[category])
            if cleaned.get("from_unit") not in valid or cleaned.get("to_unit") not in valid:
                raise forms.ValidationError("The selected units do not match the chosen category.")
        if category == "temperature" and cleaned.get("value") is not None:
            result_kelvin = _convert_temperature(
                cleaned["value"],
                UNIT_GROUPS[category][cleaned["from_unit"]],
                "K",
            ) if cleaned.get("from_unit") in UNIT_GROUPS[category] else Decimal(0)
            if result_kelvin < 0:
                raise forms.ValidationError("Temperature cannot be below absolute zero.")
        return cleaned


class PythonPracticeForm(forms.Form):
    exercise = forms.ChoiceField(
        label="Exercise",
        choices=[(str(index), f"Exercise {index + 1}") for index in range(len(PYTHON_EXERCISES))],
        initial="0",
    )
    answer = forms.ChoiceField(label="Your answer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected = self.data.get("exercise", self.initial.get("exercise", "0"))
        try:
            exercise = PYTHON_EXERCISES[int(selected)]
        except (ValueError, IndexError):
            exercise = PYTHON_EXERCISES[0]
        self.fields["answer"].choices = [(value, value) for value in exercise["options"]]


class SqlPracticeForm(forms.Form):
    example = forms.ChoiceField(
        label="Example",
        choices=(("select", "Filter and sort"), ("join", "Join tables"), ("aggregate", "Group and count")),
        initial="select",
    )
    query = forms.CharField(
        label="Your query",
        required=False,
        max_length=5000,
        initial=SQL_EXAMPLES["select"],
        widget=forms.Textarea(attrs={"rows": 8, "spellcheck": "false"}),
    )


class AreaForm(forms.Form):
    shape = forms.ChoiceField(
        choices=(
            ("rectangle", "Rectangle"),
            ("triangle", "Triangle"),
            ("circle", "Circle"),
            ("cylinder", "Cylinder"),
            ("box", "Rectangular prism"),
        )
    )
    first = BoundedDecimalField(label="Radius / length / base", min_value=0)
    second = BoundedDecimalField(label="Height / width", min_value=0, required=False)
    third = BoundedDecimalField(label="Height", min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shape = self.data.get("shape", self.initial.get("shape", "rectangle"))
        if shape == "circle":
            self.fields["first"].label = "Radius"
            self.fields.pop("second")
            self.fields.pop("third")
        elif shape == "box":
            self.fields["first"].label = "Length"
            self.fields["second"].label = "Width"
        else:
            self.fields["first"].label = "Length / base"
            self.fields.pop("third")

    def clean(self):
        cleaned = super().clean()
        shape = cleaned.get("shape")
        required = {"circle": (), "rectangle": ("second",), "triangle": ("second",),
                    "cylinder": ("second",), "box": ("second", "third")}
        for field in required.get(shape, ()):
            if cleaned.get(field) is None:
                self.add_error(field, "This dimension is required for the selected shape.")
        return cleaned


class DilutionForm(forms.Form):
    c1 = BoundedDecimalField(label="Stock concentration (C₁)", min_value=0, required=False)
    v1 = BoundedDecimalField(label="Stock volume (V₁)", min_value=0, required=False)
    c2 = BoundedDecimalField(label="Target concentration (C₂)", min_value=0, required=False)
    v2 = BoundedDecimalField(label="Final volume (V₂)", min_value=0, required=False)

    def clean(self):
        cleaned = super().clean()
        values = [cleaned.get(key) for key in ("c1", "v1", "c2", "v2")]
        if sum(value is not None for value in values) != 3:
            raise forms.ValidationError("Enter exactly three positive values for C₁V₁ = C₂V₂.")
        if any(value == 0 for value in values if value is not None):
            raise forms.ValidationError("Entered values must be greater than zero.")
        return cleaned


def _fmt(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _fmt3(value):
    return f"{value:.3f}"


def _convert_temperature(value, source, target):
    celsius = value if source == "C" else (
        (value - 32) * Decimal(5) / Decimal(9) if source == "F" else value - Decimal("273.15")
    )
    if target == "C":
        return celsius
    if target == "F":
        return celsius * Decimal(9) / Decimal(5) + 32
    return celsius + Decimal("273.15")


def _calculate_unit_conversion(data):
    category = data["category"]
    source = data["from_unit"]
    target = data["to_unit"]
    value = data["value"]
    source_factor = UNIT_GROUPS[category][source]
    target_factor = UNIT_GROUPS[category][target]
    if category == "temperature":
        result = _convert_temperature(value, source_factor, target_factor)
    else:
        result = value * source_factor / target_factor
    return f"{_fmt(result)} {target}"


def _calculate_area(data):
    shape = data["shape"]
    first = data["first"]
    second = data.get("second")
    third = data.get("third")
    if first <= 0 or (second is not None and second <= 0) or (third is not None and third <= 0):
        raise forms.ValidationError("Dimensions must be greater than zero.")
    if shape == "circle":
        return f"Area: {_fmt3(Decimal(str(math.pi)) * first * first)} square units"
    if shape == "rectangle":
        return f"Area: {_fmt3(first * second)} square units"
    if shape == "triangle":
        return f"Area: {_fmt3(first * second / 2)} square units"
    if shape == "cylinder":
        return f"Volume: {_fmt3(Decimal(str(math.pi)) * first * first * second)} cubic units"
    return f"Volume: {_fmt3(first * second * third)} cubic units"


def _calculate_ohm(data):
    voltage, current, resistance = data.get("voltage"), data.get("current"), data.get("resistance")
    if voltage is not None and current is not None:
        resistance = voltage / current if current else None
        power = voltage * current
        return f"R = {_fmt(resistance)} Ω · P = {_fmt(power)} W" if resistance is not None else f"R is undefined at 0 A · P = {_fmt(power)} W"
    if voltage is not None and resistance is not None:
        current = voltage / resistance
        return f"I = {_fmt(current)} A · P = {_fmt(voltage * current)} W"
    current = data["current"]
    resistance = data["resistance"]
    voltage = current * resistance
    return f"V = {_fmt(voltage)} V · P = {_fmt(current * current * resistance)} W"


def _calculate_dilution(data):
    keys = ("c1", "v1", "c2", "v2")
    missing = next(key for key in keys if data.get(key) is None)
    c1, v1, c2, v2 = (data.get(key) for key in keys)
    if missing == "c1":
        value, label = c2 * v2 / v1, "Stock concentration"
    elif missing == "v1":
        value, label = c2 * v2 / c1, "Stock volume needed"
    elif missing == "c2":
        value, label = c1 * v1 / v2, "Target concentration"
    else:
        value, label = c1 * v1 / c2, "Final volume"
    return f"{label}: {_fmt(value)}"


def _format_sql(query):
    query = re.sub(r"\s+", " ", query.strip())
    keywords = (
        "LEFT JOIN|RIGHT JOIN|INNER JOIN|GROUP BY|ORDER BY|INSERT INTO|DELETE FROM|"
        "SELECT|FROM|WHERE|JOIN|ON|HAVING|LIMIT|VALUES|SET|AS|AND|OR|DESC|ASC"
    )
    return re.sub(
        rf"\b({keywords})\b",
        lambda match: f"\n{match.group(1).upper()}" if match.group(1).upper() in {
            "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
            "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "VALUES", "SET"
        } else match.group(1).upper(),
        query,
        flags=re.IGNORECASE,
    ).strip()


@require_http_methods(["GET", "POST"])
def tool_detail(request, slug):
    title = TOOL_TITLES.get(slug)
    if not title:
        raise Http404("Campus tool not found.")

    form = None
    result = None
    result_detail = None
    exercise = None
    if slug == "percentage":
        form = NumberInputForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            a, b = form.cleaned_data["a"], form.cleaned_data["b"]
            if b == 0:
                form.add_error("b", "B cannot be zero.")
            else:
                result = f"{_fmt(a / b * 100)}%"
    elif slug == "cgpa":
        form = CgpaForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            grades = form.cleaned_data["grades"]
            result = _fmt(sum(grades) / len(grades))
    elif slug in {"units", "mechanical-units"}:
        mechanical = slug == "mechanical-units"
        form = UnitForm(request.POST or None, mechanical=mechanical)
        if request.method == "POST" and form.is_valid():
            result = _calculate_unit_conversion(form.cleaned_data)
    elif slug == "python":
        form = PythonPracticeForm(request.POST or None)
        selected_exercise = request.POST.get("exercise", "0") if request.method == "POST" else "0"
        try:
            exercise = PYTHON_EXERCISES[int(selected_exercise)]
        except (ValueError, IndexError):
            exercise = PYTHON_EXERCISES[0]
        if request.method == "POST" and form.is_valid():
            exercise = PYTHON_EXERCISES[int(form.cleaned_data["exercise"])]
            is_correct = form.cleaned_data["answer"] == exercise["answer"]
            result = ("Correct. " if is_correct else "Not quite. ") + exercise["explanation"]
            result_detail = "success" if is_correct else "error"
    elif slug == "sql":
        form = SqlPracticeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            result = _format_sql(form.cleaned_data["query"]) or "Your formatted query will appear here."
            result_detail = "code"
    elif slug == "linux":
        result_detail = LINUX_COMMANDS
    elif slug == "subnet":
        form = SubnetForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            network = ipaddress.ip_network(
                f"{form.cleaned_data['address']}/{form.cleaned_data['prefix']}",
                strict=False,
            )
            first = network.network_address if network.prefixlen >= 31 else network.network_address + 1
            last = network.broadcast_address if network.prefixlen >= 31 else network.broadcast_address - 1
            usable = network.num_addresses if network.prefixlen >= 31 else max(network.num_addresses - 2, 0)
            result_detail = (
                ("Subnet mask", str(network.netmask)),
                ("Network", str(network.network_address)),
                ("Broadcast", str(network.broadcast_address)),
                ("Address range", f"{first} – {last}"),
                ("Addresses", f"{usable:,} usable / {network.num_addresses:,} total"),
            )
    elif slug == "ohms-law":
        form = OhmForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            result = _calculate_ohm(form.cleaned_data)
    elif slug == "power":
        form = TwoNumbersForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            result = f"{_fmt(form.cleaned_data['first'] * form.cleaned_data['second'])} W"
    elif slug == "logic-gates":
        form = forms.Form(request.POST or None)
        form.fields["a"] = forms.BooleanField(label="A", required=False)
        form.fields["b"] = forms.BooleanField(label="B", required=False)
        values = form.data if request.method == "POST" else {}
        a, b = values.get("a") == "on", values.get("b") == "on"
        result_detail = (
            ("AND", int(a and b)),
            ("OR", int(a or b)),
            ("NAND", int(not (a and b))),
            ("XOR", int(a != b)),
            ("NOT A", int(not a)),
            ("NOT B", int(not b)),
        )
    elif slug == "area-volume":
        form = AreaForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                result = _calculate_area(form.cleaned_data)
            except forms.ValidationError as validation_error:
                form.add_error(None, validation_error)
    elif slug == "mlt-dilution":
        form = DilutionForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                result = _calculate_dilution(form.cleaned_data)
            except (DivisionByZero, ZeroDivisionError):
                form.add_error(None, "The concentration or volume used as a divisor must be greater than zero.")

    return render(
        request,
        "portal/tool_detail.html",
        {
            "title": title,
            "slug": slug,
            "form": form,
            "result": result,
            "result_detail": result_detail,
            "exercise": exercise,
        },
    )
