from decimal import Decimal, InvalidOperation
import math

from django import forms
from django.http import Http404
from django.shortcuts import render

from .branch_tool_catalog import BRANCH_TOOL_CATALOG

TOOL_DETAILS = {
    "dsa-practice": ("DSA Practice", "Practice data structures, algorithms, graph traversal and complexity with an explained question set."),
    "git-helper": ("Git & GitHub Helper", "Choose a version-control workflow to see a reviewed command sequence and safe next steps. Commands are examples only; they are never executed."),
    "stress-strain": ("Stress & Strain Calculator", "Axial-load learning calculator. Use consistent dimensions and compare assumptions with your course material."),
    "gear-ratio": ("Gear Ratio Calculator", "An ideal gear-speed estimate. Real mechanisms have losses and design constraints not represented here."),
    "heat-transfer": ("Heat Transfer Calculator", "Basic sensible heat using Q = m c ΔT. This is not a full thermodynamic-cycle solver."),
    "resistor-network": ("Series / Parallel Resistor Lab", "Ideal resistor-network calculations for learning; real circuits have tolerances and power limits."),
    "ac-power": ("AC Power Calculator", "Uses RMS values and an entered power factor for a single-phase introductory calculation."),
    "transformer-ratio": ("Transformer Ratio Calculator", "Ideal turns-ratio estimate only; it does not model losses, regulation or safety requirements."),
    "resistor-colour-code": ("Resistor Colour Code", "Decode the nominal value of a four-band resistor. Read physical parts carefully; this is a learning aid."),
    "led-resistor": ("LED Series Resistor Calculator", "Estimate a series resistor for an idealized LED circuit; verify component ratings and lab instructions."),
    "rc-time-constant": ("RC Time Constant Calculator", "Calculate a first-order RC time constant and approximate five-time-constant interval."),
    "number-base": ("Binary / Hex Converter", "Convert non-negative integers between binary, decimal and hexadecimal."),
    "concrete-volume": ("Concrete Volume Estimator", "Estimate rectangular pour volume only; structural design, mix design and code compliance are out of scope."),
    "survey-level": ("Survey Reduced-Level Calculator", "Practice the height-of-instrument method with one backsight and one staff reading."),
    "quantity-estimator": ("Quantity Cost Estimator", "A simple arithmetic estimate from quantity and unit rate; it is not a bill of quantities or construction quote."),
    "slope-grade": ("Slope / Grade Calculator", "Calculate a simple rise-over-run grade and angle. Check project standards before applying results."),
    "microscope": ("Microscope Magnification Helper", "Calculate nominal total magnification from eyepiece and objective values; actual image quality varies."),
    "lab-safety": ("Lab Safety Practice", "Educational safety scenarios only. Follow your institution's current SOPs and supervisor instructions."),
    "mlt-terminology": ("Medical Terminology Practice", "Foundational lab terminology practice for study; not for diagnosis or treatment decisions."),
}

TOOL_FIELDS = {
    "stress-strain": (
        ("force", "Axial force (N)", False),
        ("area", "Cross-sectional area (mm²)", False),
        ("length", "Original length (mm)", False),
        ("extension", "Extension (mm)", False),
    ),
    "gear-ratio": (
        ("driver_teeth", "Driver gear teeth", True),
        ("driven_teeth", "Driven gear teeth", True),
        ("input_speed", "Input speed (rpm)", False),
    ),
    "heat-transfer": (
        ("mass", "Mass (kg)", False),
        ("specific_heat", "Specific heat (kJ / kg·K)", False),
        ("temperature_change", "Temperature change (°C or K)", False),
    ),
    "resistor-network": (
        ("values", "Resistances in Ω (comma-separated)", False),
        ("voltage", "Supply voltage (V)", False),
    ),
    "ac-power": (
        ("voltage", "RMS voltage (V)", False),
        ("current", "RMS current (A)", False),
        ("power_factor", "Power factor (0–1)", False),
    ),
    "transformer-ratio": (
        ("primary_voltage", "Primary voltage (V)", False),
        ("primary_turns", "Primary turns", True),
        ("secondary_turns", "Secondary turns", True),
    ),
    "led-resistor": (
        ("supply_voltage", "Supply voltage (V)", False),
        ("forward_voltage", "LED forward voltage (V)", False),
        ("current_ma", "Target current (mA)", False),
    ),
    "rc-time-constant": (
        ("resistance", "Resistance (Ω)", False),
        ("capacitance_uf", "Capacitance (µF)", False),
    ),
    "concrete-volume": (
        ("length", "Length (m)", False),
        ("width", "Width (m)", False),
        ("depth", "Depth (m)", False),
        ("allowance", "Extra allowance (%)", False),
    ),
    "survey-level": (
        ("benchmark_rl", "Known benchmark reduced level (m)", False),
        ("backsight", "Backsight reading (m)", False),
        ("staff_reading", "Staff reading (m)", False),
    ),
    "quantity-estimator": (
        ("quantity", "Quantity", False),
        ("unit_rate", "Unit rate (₹)", False),
    ),
    "slope-grade": (
        ("rise", "Rise / vertical change", False),
        ("run", "Run / horizontal distance", False),
    ),
    "microscope": (
        ("eyepiece", "Eyepiece magnification (×)", False),
        ("objective", "Objective magnification (×)", False),
    ),
    "number-base": (
        ("value", "Non-negative integer", False),
    ),
}

COLOURS = (
    ("black", "Black"),
    ("brown", "Brown"),
    ("red", "Red"),
    ("orange", "Orange"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("blue", "Blue"),
    ("violet", "Violet"),
    ("grey", "Grey"),
    ("white", "White"),
)
TOLERANCE_COLOURS = (
    ("brown", "Brown · ±1%"),
    ("red", "Red · ±2%"),
    ("green", "Green · ±0.5%"),
    ("blue", "Blue · ±0.25%"),
    ("violet", "Violet · ±0.1%"),
    ("grey", "Grey · ±0.05%"),
    ("gold", "Gold · ±5%"),
    ("silver", "Silver · ±10%"),
)

QUIZZES = {
    "dsa-practice": (
        ("Which structure follows FIFO order?", ("Stack", "Queue", "Tree"), 1, "A queue removes items in the order they were added."),
        ("What is the average lookup complexity of a hash table?", ("O(1)", "O(n log n)", "O(n²)"), 0, "With a good hash function and controlled load factor, average lookup is O(1)."),
        ("Which traversal of a binary search tree returns sorted keys?", ("Pre-order", "In-order", "Level-order"), 1, "In-order traversal visits left subtree, node, then right subtree."),
        ("Which data structure is commonly used for breadth-first search?", ("Queue", "Stack", "Heap"), 0, "A queue processes discovered vertices in first-in, first-out order."),
        ("What is the worst-case time complexity of binary search on a sorted array?", ("O(log n)", "O(n)", "O(1)"), 0, "Binary search halves the remaining search interval on each comparison."),
        ("Which structure is best suited to last-in, first-out processing?", ("Queue", "Stack", "Graph"), 1, "A stack removes the most recently added item first."),
        ("Which operation is O(1) for an array when the index is known?", ("Read an element", "Insert at the beginning", "Search an unsorted value"), 0, "Direct indexing accesses an array element in constant time."),
        ("What is the worst-case time complexity of merge sort?", ("O(n)", "O(n log n)", "O(n²)"), 1, "Merge sort divides the input into logarithmically many levels and merges each level in O(n)."),
        ("What must be true before binary search can be used correctly?", ("The data is sorted", "The data has no duplicates", "The array length is even"), 0, "Binary search uses ordering to discard half the remaining search space."),
        ("Which traversal visits a node before its left and right subtrees?", ("In-order", "Pre-order", "Post-order"), 1, "Pre-order traversal processes the current node before its subtrees."),
        ("Which approach is commonly used to detect a cycle in a linked list with O(1) extra space?", ("Two pointers at different speeds", "Sorting the list", "A queue"), 0, "Floyd's tortoise-and-hare algorithm advances two pointers at different speeds."),
        ("What is the average time complexity of inserting into a well-sized hash table?", ("O(1)", "O(log n)", "O(n)"), 0, "With a suitable hash function and controlled load factor, insertion is average O(1)."),
        ("Which algorithmic technique solves a problem by combining solutions to smaller subproblems?", ("Divide and conquer", "Linear probing", "Breadth-first search"), 0, "Divide and conquer splits a problem, solves its parts, and combines the results."),
        ("Which data structure is most suitable for repeatedly retrieving the smallest item?", ("Min-heap", "Stack", "Linked list"), 0, "A min-heap keeps the smallest item at its root for efficient retrieval."),
        ("In an undirected graph, what does the sum of all vertex degrees equal?", ("The number of edges", "Twice the number of edges", "The number of vertices"), 1, "Every undirected edge contributes one degree to each of its two endpoints."),
    ),
    "lab-safety": (
        ("A chemical splashes into your eyes. What should you do first?", ("Keep working and report later", "Use the eyewash station and alert the supervisor", "Rub your eyes"), 1, "Follow the lab emergency procedure, use the eyewash station, and alert the supervisor immediately."),
        ("Where should a labelled specimen be handled?", ("In an approved work area using the required PPE", "In a food area", "Anywhere if the lid is closed"), 0, "Use the designated work area and follow the institution's PPE and specimen-handling SOP."),
        ("What should you do with an unlabelled sample?", ("Guess its identity", "Process it quickly", "Stop and follow the lab's rejection/escalation SOP"), 2, "Never guess a specimen identity; follow local rejection and escalation procedures."),
    ),
    "mlt-terminology": (
        ("What does 'aliquot' mean in laboratory use?", ("A measured portion of a sample", "A microscope lens", "A type of stain"), 0, "An aliquot is a measured portion taken from a larger sample."),
        ("What does 'centrifugation' use to separate components?", ("Magnetic force", "Centrifugal force from spinning", "Light refraction"), 1, "Centrifugation separates components based on their behaviour in a spinning rotor."),
        ("What is a reagent?", ("A substance used in a test or reaction", "A specimen transport box", "A microscope adjustment"), 0, "A reagent is a substance used to bring about or detect a chemical reaction."),
    ),
}

GIT_TASKS = {
    "inspect": (
        "git status\ngit diff\ngit diff --staged",
        "Review the worktree and both unstaged and staged changes before making a commit.",
    ),
    "stage": (
        "git add <file>\ngit diff --staged",
        "Stage a specific file, then inspect exactly what will enter the next commit.",
    ),
    "unstage": (
        "git restore --staged <file>",
        "Remove a file from the staging area without discarding its working-copy edits.",
    ),
    "commit": (
        'git commit -m "Describe the change"',
        "Create a local commit from staged changes. Review git status first.",
    ),
    "branch": (
        "git switch -c <branch-name>",
        "Create and switch to a feature branch before starting independent work.",
    ),
    "publish": (
        "git push -u origin <branch-name>",
        "Publish your current branch and set its upstream. Check the branch name first.",
    ),
    "sync": (
        "git status\ngit fetch origin\ngit rebase origin/<base-branch>",
        "Start with a clean worktree. Fetch updates, then rebase your feature branch onto the intended base branch.",
    ),
    "conflicts": (
        "git status\ngit diff\n# edit and review each conflicted file\ngit add <resolved-file>\ngit rebase --continue",
        "Resolve conflicts carefully and stage only reviewed files. Use git rebase --abort if you need to return to the pre-rebase state.",
    ),
}


class BranchToolForm(forms.Form):
    def __init__(self, slug, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if slug in TOOL_FIELDS:
            for name, label, integer in TOOL_FIELDS[slug]:
                if slug == "resistor-network" and name == "values":
                    self.fields[name] = forms.CharField(
                        label=label,
                        max_length=250,
                        widget=forms.TextInput(attrs={"placeholder": "100, 220, 330"}),
                    )
                elif slug == "number-base":
                    self.fields[name] = forms.CharField(
                        label=label,
                        max_length=128,
                        widget=forms.TextInput(attrs={"placeholder": "255 or 0xff or 0b11111111"}),
                    )
                else:
                    field_options = {
                        "label": label,
                        "min_value": 0,
                        "max_value": 10**12,
                    }
                    if slug == "heat-transfer" and name == "temperature_change":
                        field_options["min_value"] = -10**12
                    if slug == "concrete-volume" and name == "allowance":
                        field_options["max_value"] = 100
                    if slug == "ac-power" and name == "power_factor":
                        field_options["max_value"] = 1
                    self.fields[name] = (
                        forms.IntegerField(**field_options)
                        if integer
                        else forms.DecimalField(
                            **field_options,
                            max_digits=24,
                            decimal_places=8,
                        )
                    )
            if slug == "concrete-volume":
                self.fields["allowance"].initial = Decimal("5")
        elif slug == "resistor-colour-code":
            for name, label in (("band1", "First significant band"), ("band2", "Second significant band"), ("multiplier", "Multiplier band")):
                self.fields[name] = forms.ChoiceField(label=label, choices=COLOURS)
            self.fields["tolerance"] = forms.ChoiceField(label="Tolerance band", choices=TOLERANCE_COLOURS)
        elif slug == "git-helper":
            self.fields["task"] = forms.ChoiceField(
                label="What are you trying to do?",
                choices=[(key, key.replace("_", " ").title()) for key in GIT_TASKS],
            )
        elif slug in QUIZZES:
            self.fields["question"] = forms.IntegerField(
                min_value=0,
                max_value=len(QUIZZES[slug]) - 1,
                widget=forms.HiddenInput(),
            )
            self.fields["answer"] = forms.ChoiceField(label="Choose your answer")
            question_index = 0
            raw_index = self.data.get("question")
            if raw_index is not None:
                try:
                    question_index = int(raw_index)
                except (ValueError, TypeError):
                    question_index = 0
            if question_index not in range(len(QUIZZES[slug])):
                question_index = 0
            question = QUIZZES[slug][question_index]
            self.fields["question"].initial = question_index
            self.fields["answer"].choices = [
                (str(index), value) for index, value in enumerate(question[1])
            ]


def _decimal(value):
    return Decimal(value)


def _calculate(slug, values):
    if slug == "stress-strain":
        force, area = _decimal(values["force"]), _decimal(values["area"])
        length, extension = _decimal(values["length"]), _decimal(values["extension"])
        if area <= 0 or length <= 0:
            raise forms.ValidationError("Area and original length must be greater than zero.")
        stress_mpa = force / area
        strain = extension / length
        if strain == 0:
            return f"Stress: {stress_mpa:.4f} MPa · Strain: 0 · Young's modulus is undefined for zero extension."
        modulus_gpa = stress_mpa / strain / Decimal("1000")
        return f"Stress: {stress_mpa:.4f} MPa · Strain: {strain:.6g} · Young's modulus: {modulus_gpa:.4f} GPa"
    if slug == "gear-ratio":
        driver, driven = int(values["driver_teeth"]), int(values["driven_teeth"])
        if driver <= 0 or driven <= 0:
            raise forms.ValidationError("Both gear tooth counts must be positive integers.")
        ratio = Decimal(driven) / Decimal(driver)
        speed = _decimal(values["input_speed"]) / ratio
        return f"Reduction ratio: {ratio:.4f}:1 · Ideal output speed: {speed:.2f} rpm"
    if slug == "heat-transfer":
        heat = _decimal(values["mass"]) * _decimal(values["specific_heat"]) * _decimal(values["temperature_change"])
        return f"Sensible heat transfer: {heat:.4f} kJ"
    if slug == "resistor-network":
        try:
            resistors = [_decimal(item.strip()) for item in values["values"].split(",")]
        except InvalidOperation as error:
            raise forms.ValidationError("Enter valid comma-separated resistance values.") from error
        if not 1 <= len(resistors) <= 12 or any(
            not value.is_finite()
            or value < Decimal("0.00000001")
            or value > Decimal(10**12)
            for value in resistors
        ):
            raise forms.ValidationError(
                "Enter 1–12 resistor values from 0.00000001 Ω to 1,000,000,000,000 Ω."
            )
        equivalent = sum(resistors, Decimal(0))
        parallel = Decimal(1) / sum((Decimal(1) / value for value in resistors), Decimal(0))
        voltage = _decimal(values["voltage"])
        series_current = voltage / equivalent
        parallel_current = voltage / parallel
        return f"Series: Req {equivalent:.4f} Ω · total current {series_current:.4f} A. Parallel: Req {parallel:.4f} Ω · total current {parallel_current:.4f} A."
    if slug == "ac-power":
        voltage, current = _decimal(values["voltage"]), _decimal(values["current"])
        factor = _decimal(values["power_factor"])
        if factor > 1:
            raise forms.ValidationError("Power factor must be from 0 to 1.")
        apparent = voltage * current
        real = apparent * factor
        reactive = Decimal(str(math.sqrt(max(float(apparent**2 - real**2), 0))))
        return f"Apparent power: {apparent:.4f} VA · Real power: {real:.4f} W · Reactive power: {reactive:.4f} var"
    if slug == "transformer-ratio":
        voltage = _decimal(values["primary_voltage"])
        primary, secondary = int(values["primary_turns"]), int(values["secondary_turns"])
        if primary <= 0 or secondary <= 0:
            raise forms.ValidationError("Turn counts must be positive integers.")
        ratio = Decimal(secondary) / Decimal(primary)
        return f"Turns ratio N₂:N₁ = {secondary}:{primary} ({ratio:.4f}) · Ideal secondary voltage: {voltage * ratio:.4f} V"
    if slug == "resistor-colour-code":
        digits = {colour: index for index, (colour, _label) in enumerate(COLOURS)}
        multiplier = Decimal(10) ** digits[values["multiplier"]]
        resistance = (digits[values["band1"]] * 10 + digits[values["band2"]]) * multiplier
        tolerance = dict((key, label.split("±")[-1].rstrip("%")) for key, label in TOLERANCE_COLOURS)[values["tolerance"]]
        return f"Nominal resistance: {resistance:,} Ω · Tolerance: ±{tolerance}%"
    if slug == "led-resistor":
        supply, forward = _decimal(values["supply_voltage"]), _decimal(values["forward_voltage"])
        current = _decimal(values["current_ma"]) / Decimal(1000)
        if current <= 0 or supply <= forward:
            raise forms.ValidationError("Use positive current and a supply voltage higher than the LED forward voltage.")
        resistance = (supply - forward) / current
        dissipation = (supply - forward) * current
        return f"Calculated resistance: {resistance:.2f} Ω · Resistor dissipation: {dissipation:.4f} W. Select a suitable standard value and rating with your instructor."
    if slug == "rc-time-constant":
        tau_ms = _decimal(values["resistance"]) * _decimal(values["capacitance_uf"]) / Decimal(1000)
        return f"Time constant τ: {tau_ms:.4f} ms · Approximate 5τ settling interval: {tau_ms * 5:.4f} ms"
    if slug == "number-base":
        raw_value = values["value"].strip().lower()
        try:
            number = int(raw_value, 0) if raw_value.startswith(("0x", "0b", "0o")) else int(raw_value, 10)
        except ValueError as error:
            raise forms.ValidationError("Enter a valid decimal, 0b binary, 0o octal, or 0x hexadecimal integer.") from error
        if number < 0 or number > 2**256 - 1:
            raise forms.ValidationError("Enter a non-negative integer with at most 256 bits.")
        return f"Decimal: {number} · Binary: {bin(number)[2:]} · Hexadecimal: {hex(number)[2:].upper()}"
    if slug == "concrete-volume":
        volume = _decimal(values["length"]) * _decimal(values["width"]) * _decimal(values["depth"])
        allowance = _decimal(values["allowance"])
        if allowance > 100:
            raise forms.ValidationError("Allowance must be between 0% and 100%.")
        return f"Net volume: {volume:.4f} m³ · With allowance: {volume * (1 + allowance / 100):.4f} m³"
    if slug == "survey-level":
        benchmark = _decimal(values["benchmark_rl"])
        backsight, reading = _decimal(values["backsight"]), _decimal(values["staff_reading"])
        height_of_instrument = benchmark + backsight
        reduced_level = height_of_instrument - reading
        return f"Height of instrument: {height_of_instrument:.4f} m · Reduced level: {reduced_level:.4f} m"
    if slug == "quantity-estimator":
        quantity, unit_rate = _decimal(values["quantity"]), _decimal(values["unit_rate"])
        return f"Estimated line total: ₹{quantity * unit_rate:,.2f}"
    if slug == "slope-grade":
        rise, run = _decimal(values["rise"]), _decimal(values["run"])
        if run <= 0:
            raise forms.ValidationError("Run must be greater than zero.")
        grade = rise / run * 100
        angle = math.degrees(math.atan(float(rise / run)))
        return f"Grade: {grade:.4f}% · Slope angle: {angle:.4f}°"
    if slug == "microscope":
        eyepiece, objective = _decimal(values["eyepiece"]), _decimal(values["objective"])
        if eyepiece <= 0 or objective <= 0:
            raise forms.ValidationError("Eyepiece and objective magnification must be greater than zero.")
        total = eyepiece * objective
        return f"Total nominal magnification: {total:.0f}×"
    return None


def branch_tool_detail(request, slug):
    if slug == "web-playground":
        return render(
            request,
            "portal/web_playground.html",
            {"title": "HTML / CSS / JavaScript Playground"},
        )
    if slug not in TOOL_DETAILS:
        raise Http404("Branch tool not found.")

    title, description = TOOL_DETAILS[slug]
    result = None
    result_detail = None
    question = None
    question_number = 1
    form = BranchToolForm(slug, request.POST or None)
    if request.method == "POST" and form.is_valid():
        values = form.cleaned_data
        if slug == "git-helper":
            result, result_detail = GIT_TASKS[values["task"]]
        elif slug in QUIZZES:
            question_index = values["question"]
            selected_answer = int(values["answer"])
            current = QUIZZES[slug][question_index]
            result = ("Correct. " if selected_answer == current[2] else "Not quite. ") + current[3]
            result_detail = "success" if selected_answer == current[2] else "error"
            next_index = (question_index + 1) % len(QUIZZES[slug])
            form = BranchToolForm(slug, initial={"question": next_index})
            question = QUIZZES[slug][next_index][0]
            question_number = next_index + 1
        else:
            try:
                result = _calculate(slug, values)
            except forms.ValidationError as error:
                form.add_error(None, error)
        if slug in QUIZZES and question is None:
            question = QUIZZES[slug][form["question"].value()][0]
    else:
        if slug in QUIZZES:
            try:
                question_index = int(form["question"].value() or 0)
            except (TypeError, ValueError):
                question_index = 0
            if question_index not in range(len(QUIZZES[slug])):
                question_index = 0
            question = QUIZZES[slug][question_index][0]
            question_number = question_index + 1

    return render(
        request,
        "portal/branch_tool_detail.html",
        {
            "title": title,
            "description": description,
            "slug": slug,
            "form": form,
            "result": result,
            "result_detail": result_detail,
            "question": question,
            "question_number": question_number,
            "question_total": len(QUIZZES.get(slug, ())),
        },
    )


def branch_tool_groups(branches, selected_branch=None):
    groups = []
    selected_code = getattr(selected_branch, "code", None)
    for code, branch_data in BRANCH_TOOL_CATALOG.items():
        if selected_code and code != selected_code:
            continue
        branch = next((item for item in branches if item.code == code), None)
        groups.append(
            {
                "code": code,
                "name": branch.name if branch else branch_data["name"],
                "tools": [
                    {"name": name, "description": description, "route": route}
                    for name, description, route in branch_data["tools"]
                ],
            }
        )
    return groups
