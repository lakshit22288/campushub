import { loadPyodide } from 'pyodide'

let pyodidePromise
let pendingInput
let outputStreams

function createOutputStream(type) {
  const decoder = new TextDecoder()
  let buffered = ''
  const flush = () => {
    buffered += decoder.decode()
    if (buffered) self.postMessage({ type, text: buffered })
    buffered = ''
  }
  return {
    raw: byte => {
      buffered += decoder.decode(new Uint8Array([byte]), { stream: true })
      if (buffered.includes('\n')) flush()
    },
    flush
  }
}

function getRuntime() {
  if (!pyodidePromise) {
    pyodidePromise = loadPyodide({
      indexURL: 'https://cdn.jsdelivr.net/npm/pyodide@0.29.3/'
    })
  }
  return pyodidePromise
}

async function transformInputCalls(pyodide, source) {
  pyodide.globals.set('__campushub_source', source)
  const transformed = await pyodide.runPythonAsync(`
import ast

tree = ast.parse(__campushub_source)

class InputAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.scope = []
        self.calls = {}
        self.direct_input = set()
        self.top_level_calls = set()

    def visit_FunctionDef(self, node):
        self.calls.setdefault(node.name, set())
        self.scope.append(node.name)
        for item in node.body:
            self.visit(item)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self.scope.append(None)
        self.visit(node.body)
        self.scope.pop()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "input":
                if self.scope:
                    self.direct_input.add(self.scope[-1])
            elif self.scope:
                self.calls.setdefault(self.scope[-1], set()).add(node.func.id)
            else:
                self.top_level_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute) and self.scope:
            if isinstance(node.func.value, ast.Name) and node.func.value.id in ("self", "cls"):
                self.calls.setdefault(self.scope[-1], set()).add(node.func.attr)
        self.generic_visit(node)

analyzer = InputAnalyzer()
analyzer.visit(tree)
async_functions = {name for name in analyzer.direct_input if name is not None}
changed = True
while changed:
    changed = False
    for caller, callees in analyzer.calls.items():
        if caller not in async_functions and callees & async_functions:
            async_functions.add(caller)
            changed = True

class AsyncInputTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node = self.generic_visit(node)
        if node.name in async_functions:
            return ast.AsyncFunctionDef(
                name=node.name,
                args=node.args,
                body=node.body,
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_comment=node.type_comment,
                type_params=getattr(node, "type_params", [])
            )
        return node

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "input":
            node.func = ast.Name(id="__campushub_input", ctx=ast.Load())
            return ast.Await(value=node)
        if isinstance(node.func, ast.Name) and node.func.id in async_functions:
            return ast.Await(value=node)
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in async_functions
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in ("self", "cls")):
            return ast.Await(value=node)
        return node

tree = AsyncInputTransformer().visit(tree)
ast.fix_missing_locations(tree)
ast.unparse(tree)
`)
  try {
  return typeof transformed === 'string' ? transformed : transformed.toJs()
  } finally {
  transformed.destroy?.()
    pyodide.globals.delete('__campushub_source')
  }
}

self.onmessage = async event => {
  const { type, value, code } = event.data || {}

  if (type === 'input') {
    pendingInput?.(value)
    pendingInput = null
    return
  }
  if (type !== 'run') return

  try {
    self.postMessage({ type: 'loading' })
    const pyodide = await getRuntime()
    outputStreams = {
      stdout: createOutputStream('stdout'),
      stderr: createOutputStream('stderr')
    }
    pyodide.setStdout(outputStreams.stdout)
    pyodide.setStderr(outputStreams.stderr)
    pyodide.globals.set('__campushub_input', prompt => new Promise(resolve => {
      outputStreams.stdout.flush()
      outputStreams.stderr.flush()
      pendingInput = resolve
      self.postMessage({ type: 'input-request', prompt: String(prompt || '') })
    }))
    const transformedCode = await transformInputCalls(pyodide, code)
    self.postMessage({ type: 'running' })
    await pyodide.runPythonAsync(transformedCode)
    outputStreams.stdout.flush()
    outputStreams.stderr.flush()
    self.postMessage({ type: 'done' })
  } catch (error) {
    outputStreams?.stdout.flush()
    outputStreams?.stderr.flush()
    pendingInput = null
    self.postMessage({ type: 'error', message: error.message || 'Python could not run this program.' })
  }
}
