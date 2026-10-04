import { useEffect, useRef, useState } from 'react'
import { api } from './lib/api'

const languages = {
  c: {
    label: 'C',
    file: 'main.c',
    template: '#include <stdio.h>\n\nint main(void) {\n    char name[100];\n    if (scanf("%99s", name) != 1) return 1;\n    printf("Hello, %s!\\n", name);\n    return 0;\n}\n'
  },
  cpp: {
    label: 'C++',
    file: 'main.cpp',
    template: '#include <iostream>\n#include <string>\n\nint main() {\n    std::string name;\n    std::getline(std::cin, name);\n    std::cout << "Hello, " << name << "!" << std::endl;\n}\n'
  },
  python: {
    label: 'Python',
    file: 'main.py',
    template: 'name = input().strip()\nprint(f"Hello, {name}!")\n'
  },
  java: {
    label: 'Java',
    file: 'Main.java',
    template: 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner input = new Scanner(System.in);\n        String name = input.nextLine();\n        System.out.println("Hello, " + name + "!");\n    }\n}\n'
  },
  javascript: {
    label: 'JavaScript',
    file: 'main.js',
    template: 'const fs = require("fs");\nconst name = fs.readFileSync(0, "utf8").trim();\nconsole.log(`Hello, ${name}!`);\n'
  },
  typescript: {
    label: 'TypeScript',
    file: 'main.ts',
    template: 'import * as fs from "fs";\nconst name: string = fs.readFileSync(0, "utf8").trim();\nconsole.log(`Hello, ${name}!`);\n'
  },
  go: {
    label: 'Go',
    file: 'main.go',
    template: 'package main\n\nimport "fmt"\n\nfunc main() {\n    var name string\n    fmt.Scanln(&name)\n    fmt.Printf("Hello, %s!\\n", name)\n}\n'
  },
  rust: {
    label: 'Rust',
    file: 'main.rs',
    template: 'use std::io;\n\nfn main() {\n    let mut name = String::new();\n    io::stdin().read_line(&mut name).unwrap();\n    println!("Hello, {}!", name.trim());\n}\n'
  },
  php: {
    label: 'PHP',
    file: 'main.php',
    template: '<?php\n$name = trim(fgets(STDIN));\necho "Hello, $name!\\n";\n'
  },
  ruby: {
    label: 'Ruby',
    file: 'main.rb',
    template: 'name = STDIN.gets&.chomp\nputs "Hello, #{name}!"\n'
  }
}

const MAX_CODE_LENGTH = 50000
const MAX_INPUT_LENGTH = 10000
const PYTHON_RUNTIME_URL = 'https://cdn.jsdelivr.net/npm/pyodide@0.29.3/'
const PYTHON_RUN_TIMEOUT_MS = 20000
const PYTHON_LOAD_TIMEOUT_MS = 120000

function getOutput(result) {
  return [
    result.stdout,
    result.stderr,
    result.exception
  ].filter(Boolean).join('\n').trimEnd()
}

export default function Compiler() {
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState(languages.python.template)
  const [stdin, setStdin] = useState('CampusHub\n')
  const [result, setResult] = useState(null)
  const [liveOutput, setLiveOutput] = useState('')
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const [runnerStatus, setRunnerStatus] = useState('')
  const [inputRequest, setInputRequest] = useState(null)
  const [interactiveValue, setInteractiveValue] = useState('')
  const editor = useRef(null)
  const inputField = useRef(null)
  const workerRef = useRef(null)
  const runTimer = useRef(null)
  const runStartedAt = useRef(0)

  useEffect(() => {
    if (inputRequest !== null) inputField.current?.focus()
  }, [inputRequest])

  useEffect(() => () => {
    clearTimeout(runTimer.current)
    workerRef.current?.terminate()
  }, [])

  const stopPythonRun = message => {
    clearTimeout(runTimer.current)
    workerRef.current?.terminate()
    workerRef.current = null
    setRunning(false)
    setInputRequest(null)
    setRunnerStatus('')
    if (message) setError(message)
  }

  const changeLanguage = event => {
    const nextLanguage = event.target.value
    setLanguage(nextLanguage)
    setCode(languages[nextLanguage].template)
    setResult(null)
    setError('')
    setLiveOutput('')
    setInputRequest(null)
    setRunnerStatus('')
  }

  const startPythonRun = () => {
    setRunning(true)
    setError('')
    setResult(null)
    setLiveOutput('')
    setInputRequest(null)
    setInteractiveValue('')
    setRunnerStatus('Starting Python in your browser…')
    runStartedAt.current = Date.now()

    const worker = workerRef.current || new Worker(
      new URL('./compiler/python.worker.js', import.meta.url),
      { type: 'module' }
    )
    workerRef.current = worker
    worker.onmessage = event => {
      const message = event.data || {}
      if (message.type === 'loading') {
        setRunnerStatus('Loading Python runtime in your browser (first run may take a little longer)…')
        runTimer.current = setTimeout(
          () => stopPythonRun('Python could not load in time. Check your connection and try again.'),
          PYTHON_LOAD_TIMEOUT_MS
        )
      } else if (message.type === 'running') {
        clearTimeout(runTimer.current)
        runStartedAt.current = Date.now()
        setRunnerStatus('Running in your browser…')
        runTimer.current = setTimeout(
          () => stopPythonRun('Program stopped after 20 seconds. Check for an infinite loop, then run it again.'),
          PYTHON_RUN_TIMEOUT_MS
        )
      } else if (message.type === 'stdout' || message.type === 'stderr') {
        setLiveOutput(current => `${current}${message.text}`)
      } else if (message.type === 'input-request') {
        clearTimeout(runTimer.current)
        setRunnerStatus('')
        setInputRequest(message.prompt)
        setInteractiveValue('')
      } else if (message.type === 'done') {
        clearTimeout(runTimer.current)
        setRunning(false)
        setInputRequest(null)
        setRunnerStatus('')
        setResult({ executionTime: Date.now() - runStartedAt.current })
      } else if (message.type === 'error') {
        clearTimeout(runTimer.current)
        setRunning(false)
        setInputRequest(null)
        setRunnerStatus('')
        setResult({ exception: message.message, executionTime: Date.now() - runStartedAt.current })
      }
    }
    worker.onerror = event => {
      stopPythonRun(event.message || 'The browser Python runtime failed.')
    }

    runTimer.current = setTimeout(
      () => stopPythonRun('Python is taking too long to start. Check your connection and try again.'),
      PYTHON_LOAD_TIMEOUT_MS
    )
    worker.postMessage({ type: 'run', code })
  }

  const runCode = async () => {
    if (running) return
    if (!code.trim()) {
      setError('Add some code before running the program.')
      return
    }
    if (language === 'python') {
      startPythonRun()
      return
    }
    if (code.length > MAX_CODE_LENGTH) {
      setError(`Keep the code under ${MAX_CODE_LENGTH.toLocaleString()} characters.`)
      return
    }
    if (stdin.length > MAX_INPUT_LENGTH) {
      setError(`Keep standard input under ${MAX_INPUT_LENGTH.toLocaleString()} characters.`)
      return
    }

    setRunning(true)
    setError('')
    setResult(null)
    setLiveOutput('')

    try {
      const payload = await api('/compiler/execute', {
        method: 'POST',
        body: JSON.stringify({
          language,
          code,
          stdin
        })
      })
      setResult(payload)
    } catch (runError) {
      const timedOut = runError.name === 'TimeoutError'
      setError(timedOut || runError.status === 504
        ? 'The compiler did not respond within 20 seconds. Try a smaller program or input, and check that your code does not contain an infinite loop.'
        : runError.message || 'Could not reach the compiler service. Please try again.')
    } finally {
      setRunning(false)
    }
  }

  const submitInteractiveInput = event => {
    event.preventDefault()
    if (inputRequest === null || !workerRef.current) return
    workerRef.current.postMessage({ type: 'input', value: interactiveValue })
    setInputRequest(null)
    setInteractiveValue('')
  }

  const handleEditorKeyDown = event => {
    if (event.key === 'Tab') {
      event.preventDefault()
      const input = event.currentTarget
      const start = input.selectionStart
      const end = input.selectionEnd
      const updated = `${code.slice(0, start)}    ${code.slice(end)}`
      setCode(updated)
      requestAnimationFrame(() => {
        input.selectionStart = input.selectionEnd = start + 4
      })
    }
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault()
      runCode()
    }
  }

  const output = result ? getOutput(result) : ''
  const timedOut = result && /\b(time limit exceeded|timed out|timeout)\b/i.test(
    [result.stderr, result.exception].filter(Boolean).join('\n')
  )
  const failed = result && Boolean(result.stderr || result.exception)
  const displayedOutput = language === 'python'
    ? `${liveOutput}${result?.exception ? `${liveOutput ? '\n' : ''}${result.exception}` : ''}`.trimEnd()
    : output

  return <div className="compiler-page">
    <section className="compiler-intro">
      <div>
        <span className="eyebrow">CAMPUSHUB CODE LAB</span>
        <h2>Think it.<br/><em>Run it.</em></h2>
        <p>Run Python interactively in your browser, with nine more languages available through cloud execution.</p>
      </div>
      <div className="compiler-language-count"><strong>10</strong><span>languages available</span></div>
    </section>

    <section className="compiler-panel" aria-label="Code editor">
      <div className="compiler-toolbar">
        <label className="compiler-language">Language
          <select value={language} onChange={changeLanguage} disabled={running}>
            {Object.entries(languages).map(([value, item]) => <option value={value} key={value}>{item.label}</option>)}
          </select>
        </label>
        <div className="compiler-toolbar-actions">
          <span className="compiler-file">{languages[language].file}</span>
          <button
            className="compiler-reset"
            onClick={() => {
              setCode(languages[language].template)
              setStdin('CampusHub\n')
              setResult(null)
              setError('')
            }}
          >
            Reset example
          </button>
          {running
            ? <button className="btn compiler-stop" onClick={() => stopPythonRun('Run stopped.')}>Stop</button>
            : <button className="btn primary compiler-run" onClick={runCode}>Run code</button>}
        </div>
      </div>

      <div className="compiler-editor">
        <div className="compiler-gutter" aria-hidden="true">
          {code.split('\n').map((_, index) => <span key={index}>{index + 1}</span>)}
        </div>
        <textarea
          ref={editor}
          aria-label={`${languages[language].label} source code`}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          maxLength={MAX_CODE_LENGTH}
          onChange={event => setCode(event.target.value)}
          onKeyDown={handleEditorKeyDown}
          spellCheck="false"
          value={code}
        />
      </div>

      <div className="compiler-lower">
        {language === 'python'
          ? <section className="compiler-input compiler-live-input" aria-label="Live program input">
            <strong>Live program input</strong>
            <div className="compiler-live-console" aria-live="polite">
              {inputRequest !== null
                ? <form onSubmit={submitInteractiveInput}>
                  {inputRequest && <label htmlFor="compiler-live-response" className="compiler-live-prompt">{inputRequest}</label>}
                  <div className="compiler-live-response-row">
                    <input
                      ref={inputField}
                      id="compiler-live-response"
                      value={interactiveValue}
                      onChange={event => setInteractiveValue(event.target.value)}
                      aria-label="Response to the running program"
                      autoComplete="off"
                    />
                    <button className="btn primary compiler-send" type="submit">Send</button>
                  </div>
                </form>
                : <span>{runnerStatus || (running ? 'Python program is running…' : 'When input() runs, respond here and the program will continue.')}</span>}
            </div>
          </section>
          : <label className="compiler-input">Program input <span className="compiler-input-hint">Enter input before Run · one value per line</span>
            <textarea
              maxLength={MAX_INPUT_LENGTH}
              onChange={event => setStdin(event.target.value)}
              placeholder="For example: CampusHub"
              value={stdin}
            />
          </label>}
        <section className={`compiler-output${failed ? ' has-error' : ''}`} aria-live="polite">
          <div className="compiler-output-head">
            <strong>Output</strong>
            {result && <span>{timedOut ? 'Time limit exceeded' : failed ? 'Finished with errors' : `Finished · ${result.executionTime} ms`}</span>}
            {!result&&!error&&!running&&<span>Waiting to run</span>}
            {running&&<span>{language === 'python' ? 'Running in browser…' : 'Running code with your input…'}</span>}
          </div>
          <pre>{error || (result ? displayedOutput || (failed ? 'The program did not produce output.' : 'Program completed with no output.') : language === 'python' ? liveOutput || 'Run your code. Any input() call will pause here for your response.' : 'Run your code to see the result here.')}</pre>
        </section>
      </div>
      <div className="compiler-footnote">
        <span>Shortcuts: Tab to indent · Ctrl/⌘ + Enter to run</span>
        <span>{language === 'python'
          ? `Python runs in your browser; input() pauses for your response. Its runtime is downloaded from ${PYTHON_RUNTIME_URL} on first use; your code stays in this browser.`
          : 'Code and pre-entered input are sent to OneCompiler via CampusHub’s API. Don’t include private data.'}</span>
      </div>
    </section>
  </div>
}
