(function () {
  "use strict";

  const terminal = document.querySelector("[data-linux-terminal]");
  if (!terminal) return;

  const form = terminal.querySelector(".linux-terminal-form");
  const input = form.querySelector("input[name='command']");
  const output = terminal.querySelector(".linux-terminal-output");
  const clear = terminal.querySelector(".linux-clear");
  const prompt = terminal.querySelector("#linux-prompt");
  const initialFiles = {
    "home": {
      "student": {
        "README.md": "# Welcome\nThis is your temporary CampuZHub Linux practice workspace.",
        "notes.txt": "Linux is a multi-user operating system.\nThe shell interprets commands.",
        "projects": {
          "README.md": "Practice navigating, reading, and organizing project files.",
          "starter.py": "print('Hello from the practice workspace!')",
        },
      },
    },
  };
  let files = clone(initialFiles);
  let currentPath = ["home", "student"];

  function clone(value) {
    if (typeof structuredClone === "function") return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function tokenize(line) {
    const tokens = [];
    const expression = /"([^"]*)"|'([^']*)'|(\S+)/g;
    let match;
    while ((match = expression.exec(line))) {
      tokens.push(match[1] !== undefined ? match[1] : match[2] !== undefined ? match[2] : match[3]);
    }
    return tokens;
  }

  function resolvePath(path) {
    const homePath = path === "~" || path.startsWith("~/");
    const segments = homePath ? ["home", "student"] : path.startsWith("/") ? [] : currentPath.slice();
    const inputPath = homePath ? path.slice(2) : path;
    for (const part of inputPath.split("/")) {
      if (!part || part === ".") continue;
      if (part === "..") segments.pop();
      else segments.push(part);
    }
    let node = files;
    for (const part of segments) {
      if (!node || typeof node !== "object" || !(part in node)) {
        return { segments, node: null };
      }
      node = node[part];
    }
    return { segments, node };
  }

  function parentFor(path) {
    const resolved = resolvePath(path);
    if (!resolved.segments.length) return null;
    const name = resolved.segments.pop();
    const parent = resolvePath("/" + resolved.segments.join("/")).node;
    return parent && typeof parent === "object" ? { parent, name, resolved } : null;
  }

  function displayPath(path) {
    return "/" + path.join("/");
  }

  function displayPromptPath(path) {
    const home = ["home", "student"];
    if (path.length >= home.length && home.every((part, index) => path[index] === part)) {
      const suffix = path.slice(home.length);
      return suffix.length ? "~/" + suffix.join("/") : "~";
    }
    return displayPath(path);
  }

  function updatePrompt() {
    prompt.textContent = "student@campushub:" + displayPromptPath(currentPath) + "$";
  }

  function print(text, className) {
    const line = document.createElement("p");
    line.textContent = text;
    if (className) line.className = className;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
  }

  function run(line) {
    const args = tokenize(line);
    const command = args.shift();
    if (!command) return;

    if (command === "help") {
      return "Commands: pwd, ls [path], cd <path>, cat <file>, grep <text> <file>, mkdir <dir>, touch <file>, echo <text> > <file>, cp <file> <destination>, mv <file> <destination>, rm <file>, clear.";
    }
    if (command === "pwd") return displayPath(currentPath);
    if (command === "ls") {
      const path = args.find((arg) => !arg.startsWith("-")) || ".";
      const node = resolvePath(path).node;
      if (!node || typeof node !== "object") return "ls: directory not found";
      const names = Object.keys(node).sort();
      return names.length ? names.map((name) => typeof node[name] === "object" ? name + "/" : name).join("   ") : "(empty directory)";
    }
    if (command === "cd") {
      const target = resolvePath(args[0] || "~");
      if (!target.node || typeof target.node !== "object") return "cd: directory not found";
      currentPath = args[0] === "~" ? ["home", "student"] : target.segments;
      updatePrompt();
      return "Directory changed to " + displayPromptPath(currentPath);
    }
    if (command === "cat") {
      const target = resolvePath(args[0] || "");
      return typeof target.node === "string" ? target.node : "cat: file not found";
    }
    if (command === "grep") {
      const path = args[args.length - 1] || "";
      const pattern = args.slice(0, -1).join(" ");
      const content = resolvePath(path).node;
      if (typeof content !== "string") return "grep: file not found";
      const matches = content.split("\n").filter((item) => item.includes(pattern));
      return matches.length ? matches.join("\n") : "No matching lines.";
    }
    if (command === "mkdir" || command === "touch") {
      const target = parentFor(args[0] || "");
      if (!target) return command + ": invalid path";
      if (target.parent[target.name] !== undefined) return command + ": path already exists";
      target.parent[target.name] = command === "mkdir" ? {} : "";
      return command === "mkdir"
        ? "Created directory: " + target.name
        : "Created file: " + target.name;
    }
    if (command === "echo") {
      const redirectIndex = args.indexOf(">");
      if (redirectIndex < 0) return args.join(" ");
      const path = args[redirectIndex + 1];
      const target = parentFor(path || "");
      if (!target || (target.parent[target.name] !== undefined && typeof target.parent[target.name] !== "string")) {
        return "echo: destination must be a file path";
      }
      target.parent[target.name] = args.slice(0, redirectIndex).join(" ");
      return "Saved text to " + path;
    }
    if (command === "cp" || command === "mv") {
      const source = parentFor(args[0] || "");
      let destinationPath = args[1] || "";
      if (!source || typeof source.parent[source.name] !== "string") return command + ": source file not found";
      const existingDestination = resolvePath(destinationPath);
      if (existingDestination.node && typeof existingDestination.node === "object") {
        destinationPath = destinationPath.replace(/\/$/, "") + "/" + source.name;
      }
      const destination = parentFor(destinationPath);
      if (!destination) return command + ": destination file path not found";
      if (
        source.parent === destination.parent &&
        source.name === destination.name
      ) return command + ": source and destination are the same file";
      destination.parent[destination.name] = source.parent[source.name];
      if (command === "mv") delete source.parent[source.name];
      return (command === "cp" ? "Copied " : "Moved ") + source.name + " to " + destination.name;
    }
    if (command === "rm") {
      const target = parentFor(args[0] || "");
      if (!target || typeof target.parent[target.name] !== "string") return "rm: file not found (directories are protected)";
      delete target.parent[target.name];
      return "Removed from the temporary practice workspace.";
    }
    if (command === "clear") {
      output.replaceChildren();
      return "";
    }
    return command + ": command not found. Type help to see available commands.";
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const command = input.value.trim();
    if (!command) return;
    print(prompt.textContent + " " + command, "linux-terminal-command");
    const result = run(command);
    if (result) print(result);
    input.value = "";
    input.focus();
  });

  clear.addEventListener("click", function () {
    output.replaceChildren();
    input.focus();
  });
})();
