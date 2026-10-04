import { randomUUID } from 'node:crypto'
import { Router } from 'express'

const router = Router()

const runtimes = {
  c: { name: 'C', version: 'latest', mode: 'c_cpp', extension: 'c', file: 'Main.c' },
  cpp: { name: 'C++', version: 'latest', mode: 'c_cpp', extension: 'cpp', file: 'Main.cpp' },
  python: { name: 'Python', version: '3.6', mode: 'python', extension: 'py', file: 'main.py' },
  java: { name: 'Java', version: '11', mode: 'java', extension: 'java', file: 'Main.java' },
  javascript: { name: 'JavaScript', version: 'ES6', mode: 'javascript', extension: 'js', file: 'index.js' },
  typescript: { name: 'TypeScript', version: '3.12', mode: 'javascript', extension: 'ts', file: 'main.ts' },
  go: { name: 'Go', version: '1.12', mode: 'golang', extension: 'go', file: 'main.go' },
  rust: { name: 'Rust', mode: 'c_cpp', extension: 'rs', file: 'HelloWorld.rs' },
  php: { name: 'PHP', mode: 'java', extension: 'php', file: 'HelloWorld.php' },
  ruby: { name: 'Ruby', mode: 'ruby', extension: 'rb', file: 'HelloWorld.rb' }
}

const MAX_CODE_LENGTH = 50000
const MAX_INPUT_LENGTH = 10000
const UPSTREAM_TIMEOUT_MS = 20000

router.post('/execute', async (req, res) => {
  const { language, code, stdin = '' } = req.body || {}
  const runtime = Object.hasOwn(runtimes, language) ? runtimes[language] : null

  if (!runtime) return res.status(400).json({ message: 'Choose a supported programming language.' })
  if (typeof code !== 'string' || !code.trim()) {
    return res.status(400).json({ message: 'Add some code before running the program.' })
  }
  if (code.length > MAX_CODE_LENGTH) {
    return res.status(413).json({ message: `Code must be ${MAX_CODE_LENGTH.toLocaleString()} characters or fewer.` })
  }
  if (typeof stdin !== 'string' || stdin.length > MAX_INPUT_LENGTH) {
    return res.status(413).json({ message: `Standard input must be ${MAX_INPUT_LENGTH.toLocaleString()} characters or fewer.` })
  }

  const payload = {
    name: runtime.name,
    title: `CampusHub-${randomUUID()}`,
    mode: runtime.mode,
    extension: runtime.extension,
    languageType: 'programming',
    active: true,
    properties: {
      language,
      files: [{ name: runtime.file, content: code }],
      stdin
    }
  }
  if (runtime.version) payload.version = runtime.version

  try {
    const response = await fetch('https://onecompiler.com/api/code/exec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS)
    })
    const body = await response.text()
    let result
    try {
      result = body ? JSON.parse(body) : {}
    } catch {
      console.error('OneCompiler returned an unreadable response.')
      return res.status(502).json({ message: 'The compiler service returned an unreadable response.' })
    }
    if (!response.ok) {
      console.error(`OneCompiler request failed with HTTP ${response.status}.`)
      return res.status(502).json({ message: 'The compiler service could not run this program. Please try again.' })
    }

    return res.json({
      stdout: typeof result.stdout === 'string' ? result.stdout : '',
      stderr: typeof result.stderr === 'string' ? result.stderr : '',
      exception: typeof result.exception === 'string' ? result.exception : null,
      compilationTime: result.compilationTime ?? null,
      executionTime: result.executionTime ?? null
    })
  } catch (error) {
    if (error.name === 'TimeoutError') {
      return res.status(504).json({ message: 'The compiler took too long to respond. Please try again.' })
    }
    console.error('Could not reach OneCompiler:', error)
    return res.status(502).json({ message: 'Could not reach the compiler service. Please try again.' })
  }
})

export default router
