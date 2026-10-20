(function () {
  "use strict";

  const form = document.querySelector(".sql-lab-form");
  if (!form) return;

  const example = form.querySelector("#id_example");
  const query = form.querySelector("#id_query");
  const examples = {
    select: "SELECT name, branch, semester, cgpa\nFROM students\nWHERE semester >= 3\nORDER BY cgpa DESC;",
    join: "SELECT students.name, subjects.name AS subject, enrollments.score\nFROM students\nJOIN enrollments ON enrollments.student_id = students.id\nJOIN subjects ON subjects.id = enrollments.subject_id\nORDER BY students.name, subjects.name;",
    aggregate: "SELECT branch, COUNT(*) AS student_count, ROUND(AVG(cgpa), 2) AS average_cgpa\nFROM students\nGROUP BY branch\nORDER BY student_count DESC;",
  };

  example.addEventListener("change", function () {
    if (examples[example.value]) query.value = examples[example.value];
  });

  query.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      form.requestSubmit(form.querySelector('[name="action"][value="run"]'));
    }
  });
})();
