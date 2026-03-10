import { execSync, spawn } from 'child_process'
import { existsSync, mkdirSync, writeFileSync, copyFileSync, readdirSync, statSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

const PYTHON_VERSION = '3.11'
const PYTHON_EMBED_URL = `https://www.python.org/ftp/python/${PYTHON_VERSION}.9/python-${PYTHON_VERSION}.9-embed-amd64.zip`

function log(message) {
  console.log(`[build-python] ${message}`)
}

function error(message) {
  console.error(`[build-python] ERROR: ${message}`)
}

function execCommand(command, options = {}) {
  try {
    return execSync(command, { 
      stdio: 'inherit',
      encoding: 'utf-8',
      ...options 
    })
  } catch (err) {
    throw new Error(`Command failed: ${command}\n${err.message}`)
  }
}

function copyDirectory(src, dest) {
  if (!existsSync(dest)) {
    mkdirSync(dest, { recursive: true })
  }
  
  const entries = readdirSync(src)
  for (const entry of entries) {
    const srcPath = join(src, entry)
    const destPath = join(dest, entry)
    
    if (statSync(srcPath).isDirectory()) {
      copyDirectory(srcPath, destPath)
    } else {
      copyFileSync(srcPath, destPath)
    }
  }
}

async function downloadPythonEmbed() {
  const pythonDir = join(projectRoot, 'resources', 'python')
  const zipPath = join(projectRoot, 'resources', 'python-embed.zip')
  
  if (existsSync(join(pythonDir, 'python.exe'))) {
    log('Python embed already exists, skipping download')
    return pythonDir
  }
  
  log('Downloading Python embed...')
  mkdirSync(dirname(zipPath), { recursive: true })
  
  if (process.platform === 'win32') {
    execCommand(`curl -L -o "${zipPath}" "${PYTHON_EMBED_URL}"`)
    execCommand(`powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${pythonDir}' -Force"`)
  } else {
    execCommand(`wget -O "${zipPath}" "${PYTHON_EMBED_URL}"`)
    execCommand(`unzip -o "${zipPath}" -d "${pythonDir}"`)
  }
  
  log('Python embed downloaded and extracted')
  return pythonDir
}

async function installPythonDeps(pythonDir) {
  log('Installing Python dependencies...')
  
  const pipPath = join(pythonDir, 'Scripts', 'pip.exe') || join(pythonDir, 'pip.exe')
  const requirementsPath = join(projectRoot, 'one_to_two_V2', 'requirements.txt')
  
  if (!existsSync(pipPath)) {
    log('Installing pip...')
    const getPipPath = join(projectRoot, 'resources', 'get-pip.py')
    execCommand(`curl -L -o "${getPipPath}" https://bootstrap.pypa.io/get-pip.py`)
    execCommand(`"${join(pythonDir, 'python.exe')}" "${getPipPath}"`)
  }
  
  log('Installing requirements...')
  execCommand(`"${join(pythonDir, 'python.exe')}" -m pip install -r "${requirementsPath}" --target "${join(pythonDir, 'Lib', 'site-packages')}"`)
  
  log('Python dependencies installed')
}

async function createPortablePython() {
  log('Creating portable Python environment...')
  
  const resourcesDir = join(projectRoot, 'resources')
  const pythonDir = join(resourcesDir, 'python')
  
  mkdirSync(resourcesDir, { recursive: true })
  
  if (process.platform === 'win32') {
    await downloadPythonEmbed()
    await installPythonDeps(pythonDir)
  } else {
    log('Non-Windows platform detected. Using system Python.')
    log('For production builds, consider using PyInstaller or similar tools.')
  }
  
  log('Portable Python environment created')
}

async function createVenvAndInstall() {
  log('Creating virtual environment...')
  
  const venvPath = join(projectRoot, 'resources', 'python-venv')
  const requirementsPath = join(projectRoot, 'one_to_two_V2', 'requirements.txt')
  
  if (process.platform === 'win32') {
    execCommand(`python -m venv "${venvPath}"`)
    execCommand(`"${join(venvPath, 'Scripts', 'pip.exe')}" install -r "${requirementsPath}"`)
  } else {
    execCommand(`python3 -m venv "${venvPath}"`)
    execCommand(`"${join(venvPath, 'bin', 'pip')}" install -r "${requirementsPath}"`)
  }
  
  log('Virtual environment created and dependencies installed')
}

async function main() {
  const args = process.argv.slice(2)
  const method = args[0] || 'venv'
  
  log(`Building Python environment (method: ${method})...`)
  
  try {
    if (method === 'embed') {
      await createPortablePython()
    } else if (method === 'venv') {
      await createVenvAndInstall()
    } else {
      error(`Unknown method: ${method}`)
      error('Usage: node scripts/build-python.js [embed|venv]')
      process.exit(1)
    }
    
    log('Python environment build completed successfully!')
  } catch (err) {
    error(err.message)
    process.exit(1)
  }
}

main()
