BRANCH_TOOL_CATALOG = {
    "CSE": {
        "name": "Computer Science / IT",
        "tools": (
            ("Multi-language Code Lab", "Run Python in the browser and other supported languages through the hosted compiler.", "/compiler/"),
            ("HTML / CSS / JavaScript Playground", "Build a small web page in an isolated browser preview.", "/branch-tools/web-playground/"),
            ("SQL Query Practice", "Run read-only SQL against a fictional, in-memory dataset and inspect results.", "/tools/sql/"),
            ("DSA Practice", "Practice data structures, algorithms, graph traversal and complexity with explained questions.", "/branch-tools/dsa-practice/"),
            ("Linux Command Practice", "Use a simulated terminal to practice shell commands in a temporary virtual filesystem.", "/tools/linux/"),
            ("Git & GitHub Helper", "Review safe, step-by-step workflows for common Git tasks; commands are never run.", "/branch-tools/git-helper/"),
        ),
    },
    "ME": {
        "name": "Mechanical Engineering",
        "tools": (
            ("Mechanical Unit Converter", "Convert pressure, force, torque, power and speed.", "/tools/mechanical-units/"),
            ("Area & Volume Calculator", "Work through common area and volume calculations.", "/tools/area-volume/"),
            ("Stress & Strain Calculator", "Calculate axial stress, strain and Young's modulus from consistent inputs.", "/branch-tools/stress-strain/"),
            ("Gear Ratio Calculator", "Estimate ideal output speed from tooth counts and input speed.", "/branch-tools/gear-ratio/"),
            ("Heat Transfer Calculator", "Use Q = m c ΔT for a basic sensible-heat calculation.", "/branch-tools/heat-transfer/"),
        ),
    },
    "EE": {
        "name": "Electrical Engineering",
        "tools": (
            ("Ohm's Law Calculator", "Solve for voltage, current, resistance and power from two known values.", "/tools/ohms-law/"),
            ("DC Power Calculator", "Calculate electrical power from voltage and current.", "/tools/power/"),
            ("Series / Parallel Resistor Lab", "Compare equivalent resistance and total current for a resistor network.", "/branch-tools/resistor-network/"),
            ("AC Power Calculator", "Explore apparent, real and reactive power using RMS values and power factor.", "/branch-tools/ac-power/"),
            ("Transformer Ratio Calculator", "Estimate ideal secondary voltage from a turns ratio.", "/branch-tools/transformer-ratio/"),
        ),
    },
    "ECE": {
        "name": "Electronics and Communication Engineering (ECE)",
        "tools": (
            ("Logic Gate Helper", "Inspect truth-table outputs for common logic gates.", "/tools/logic-gates/"),
            ("Resistor Colour Code", "Decode a four-band resistor value and tolerance.", "/branch-tools/resistor-colour-code/"),
            ("LED Series Resistor Calculator", "Estimate a current-limiting resistor and its dissipation for learning circuits.", "/branch-tools/led-resistor/"),
            ("RC Time Constant Calculator", "Calculate τ and an approximate five-time-constant settling interval.", "/branch-tools/rc-time-constant/"),
            ("Binary / Hex Converter", "Convert bounded non-negative integers between binary, decimal and hexadecimal.", "/branch-tools/number-base/"),
        ),
    },
    "CE": {
        "name": "Civil Engineering",
        "tools": (
            ("Area & Volume Calculator", "Calculate common geometry measurements with consistent units.", "/tools/area-volume/"),
            ("Concrete Volume Estimator", "Estimate a simple rectangular pour volume with an optional material allowance.", "/branch-tools/concrete-volume/"),
            ("Survey Reduced-Level Calculator", "Practice height-of-instrument reduced-level calculations.", "/branch-tools/survey-level/"),
            ("Quantity Cost Estimator", "Add quantity and unit-rate line items for a basic estimate.", "/branch-tools/quantity-estimator/"),
            ("Slope / Grade Calculator", "Calculate rise, run, grade percentage and angle.", "/branch-tools/slope-grade/"),
        ),
    },
    "MLT": {
        "name": "Medical Laboratory Technology",
        "tools": (
            ("Solution Dilution Calculator", "Practice C₁V₁ = C₂V₂ with consistent units; verify lab work with faculty.", "/tools/mlt-dilution/"),
            ("Microscope Magnification Helper", "Calculate total magnification from eyepiece and objective values.", "/branch-tools/microscope/"),
            ("Lab Safety Practice", "Review basic laboratory safety decisions with an educational quiz.", "/branch-tools/lab-safety/"),
            ("Medical Terminology Practice", "Practice foundational laboratory terminology with answer explanations.", "/branch-tools/mlt-terminology/"),
            ("Medical Unit Converter", "Convert selected mass, volume and temperature units for coursework.", "/tools/units/"),
        ),
    },
}

BRANCH_TOOL_SLUGS = {
    "web-playground",
    "dsa-practice",
    "git-helper",
    "stress-strain",
    "gear-ratio",
    "heat-transfer",
    "resistor-network",
    "ac-power",
    "transformer-ratio",
    "resistor-colour-code",
    "led-resistor",
    "rc-time-constant",
    "number-base",
    "concrete-volume",
    "survey-level",
    "quantity-estimator",
    "slope-grade",
    "microscope",
    "lab-safety",
    "mlt-terminology",
}
