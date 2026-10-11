import json
import logging
from uuid import uuid4

import httpx
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 50_000
MAX_INPUT_LENGTH = 10_000
MAX_REQUEST_BODY_SIZE = 400_000
MAX_UPSTREAM_RESPONSE_SIZE = 1_000_000
UPSTREAM_TIMEOUT_SECONDS = 20

LANGUAGES = {
    "c": {
        "label": "C",
        "file": "main.c",
        "template": '#include <stdio.h>\n\nint main(void) {\n    char name[100];\n    if (scanf("%99s", name) != 1) return 1;\n    printf("Hello, %s!\\n", name);\n    return 0;\n}\n',
        "name": "C",
        "version": "latest",
        "mode": "c_cpp",
        "extension": "c",
        "runtime_file": "Main.c",
    },
    "cpp": {
        "label": "C++",
        "file": "main.cpp",
        "template": '#include <iostream>\n#include <string>\n\nint main() {\n    std::string name;\n    std::getline(std::cin, name);\n    std::cout << "Hello, " << name << "!" << std::endl;\n}\n',
        "name": "C++",
        "version": "latest",
        "mode": "c_cpp",
        "extension": "cpp",
        "runtime_file": "Main.cpp",
    },
    "python": {
        "label": "Python",
        "file": "main.py",
        "template": 'name = input().strip()\nprint(f"Hello, {name}!")\n',
    },
    "java": {
        "label": "Java",
        "file": "Main.java",
        "template": 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner input = new Scanner(System.in);\n        String name = input.nextLine();\n        System.out.println("Hello, " + name + "!");\n    }\n}\n',
        "name": "Java",
        "version": "11",
        "mode": "java",
        "extension": "java",
        "runtime_file": "Main.java",
    },
    "javascript": {
        "label": "JavaScript",
        "file": "main.js",
        "template": 'const fs = require("fs");\nconst name = fs.readFileSync(0, "utf8").trim();\nconsole.log(`Hello, ${name}!`);\n',
        "name": "JavaScript",
        "version": "ES6",
        "mode": "javascript",
        "extension": "js",
        "runtime_file": "index.js",
    },
    "typescript": {
        "label": "TypeScript",
        "file": "main.ts",
        "template": 'import * as fs from "fs";\nconst name: string = fs.readFileSync(0, "utf8").trim();\nconsole.log(`Hello, ${name}!`);\n',
        "name": "TypeScript",
        "version": "3.12",
        "mode": "javascript",
        "extension": "ts",
        "runtime_file": "main.ts",
    },
    "go": {
        "label": "Go",
        "file": "main.go",
        "template": 'package main\n\nimport "fmt"\n\nfunc main() {\n    var name string\n    fmt.Scanln(&name)\n    fmt.Printf("Hello, %s!\\n", name)\n}\n',
        "name": "Go",
        "version": "1.12",
        "mode": "golang",
        "extension": "go",
        "runtime_file": "main.go",
    },
    "rust": {
        "label": "Rust",
        "file": "main.rs",
        "template": 'use std::io;\n\nfn main() {\n    let mut name = String::new();\n    io::stdin().read_line(&mut name).unwrap();\n    println!("Hello, {}!", name.trim());\n}\n',
        "name": "Rust",
        "mode": "c_cpp",
        "extension": "rs",
        "runtime_file": "HelloWorld.rs",
    },
    "php": {
        "label": "PHP",
        "file": "main.php",
        "template": '<?php\n$name = trim(fgets(STDIN));\necho "Hello, $name!\\n";\n',
        "name": "PHP",
        "mode": "java",
        "extension": "php",
        "runtime_file": "HelloWorld.php",
    },
    "ruby": {
        "label": "Ruby",
        "file": "main.rb",
        "template": 'name = STDIN.gets&.chomp\nputs "Hello, #{name}!"\n',
        "name": "Ruby",
        "mode": "ruby",
        "extension": "rb",
        "runtime_file": "HelloWorld.rb",
    },
}


def compiler_page(request):
    return render(
        request,
        "portal/compiler.html",
        {
            "languages": {
                key: {
                    "label": values["label"],
                    "file": values["file"],
                    "template": values["template"],
                }
                for key, values in LANGUAGES.items()
            },
            "max_code_length": MAX_CODE_LENGTH,
            "max_input_length": MAX_INPUT_LENGTH,
        },
    )


def _json_error(message, status):
    return JsonResponse({"message": message}, status=status)


@require_POST
def execute_code(request):
    if request.content_type != "application/json":
        return _json_error("Compiler request must use JSON.", 415)
    if len(request.body) > MAX_REQUEST_BODY_SIZE:
        return _json_error("Compiler request is too large.", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_error("Compiler request must contain valid JSON.", 400)
    if not isinstance(payload, dict):
        return _json_error("Compiler request must be a JSON object.", 400)

    language = payload.get("language")
    code = payload.get("code")
    stdin = payload.get("stdin", "")
    runtime = LANGUAGES.get(language) if isinstance(language, str) else None
    if not runtime or "name" not in runtime:
        return _json_error("Choose a supported programming language.", 400)
    if not isinstance(code, str) or not code.strip():
        return _json_error("Add some code before running the program.", 400)
    if len(code) > MAX_CODE_LENGTH:
        return _json_error(f"Code must be {MAX_CODE_LENGTH:,} characters or fewer.", 413)
    if not isinstance(stdin, str):
        return _json_error("Standard input must be text.", 400)
    if len(stdin) > MAX_INPUT_LENGTH:
        return _json_error(f"Standard input must be {MAX_INPUT_LENGTH:,} characters or fewer.", 413)

    upstream_payload = {
        "name": runtime["name"],
        "title": f"CampusHub-{uuid4()}",
        "mode": runtime["mode"],
        "extension": runtime["extension"],
        "languageType": "programming",
        "active": True,
        "properties": {
            "language": language,
            "files": [{"name": runtime["runtime_file"], "content": code}],
            "stdin": stdin,
        },
    }
    if runtime.get("version"):
        upstream_payload["version"] = runtime["version"]

    try:
        with httpx.Client(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
            with client.stream(
                "POST",
                "https://onecompiler.com/api/code/exec",
                json=upstream_payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response_body = bytearray()
                response_too_large = False
                for chunk in response.iter_bytes():
                    if len(response_body) + len(chunk) > MAX_UPSTREAM_RESPONSE_SIZE:
                        response_too_large = True
                        break
                    response_body.extend(chunk)
                response_status = response.status_code
    except httpx.TimeoutException:
        logger.warning("OneCompiler request timed out")
        return _json_error("The compiler took too long to respond. Please try again.", 504)
    except httpx.RequestError:
        logger.exception("Could not reach OneCompiler")
        return _json_error("Could not reach the compiler service. Please try again.", 502)

    if response_too_large:
        logger.warning("OneCompiler response exceeded the output size limit")
        return _json_error("The compiler response was too large to display.", 502)
    try:
        result = json.loads(response_body)
    except (ValueError, UnicodeDecodeError):
        logger.error("OneCompiler returned an unreadable response")
        return _json_error("The compiler service returned an unreadable response.", 502)
    if not 200 <= response_status < 300:
        logger.error("OneCompiler request failed with HTTP %s", response_status)
        return _json_error("The compiler service could not run this program. Please try again.", 502)
    if not isinstance(result, dict):
        logger.error("OneCompiler returned an invalid response shape")
        return _json_error("The compiler service returned an invalid response.", 502)

    return JsonResponse(
        {
            "stdout": result.get("stdout") if isinstance(result.get("stdout"), str) else "",
            "stderr": result.get("stderr") if isinstance(result.get("stderr"), str) else "",
            "exception": result.get("exception") if isinstance(result.get("exception"), str) else None,
            "compilationTime": result.get("compilationTime")
            if isinstance(result.get("compilationTime"), (int, float))
            else None,
            "executionTime": result.get("executionTime")
            if isinstance(result.get("executionTime"), (int, float))
            else None,
        }
    )
