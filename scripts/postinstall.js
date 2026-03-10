import { execSync } from 'child_process'
import { existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

function log(message) {
  console.log(`[postinstall] ${message}`)
}

function runCommand(command, silent = false) {
  try {
    execSync(command, { 
      stdio: silent ? 'pipe' : 'inherit',
      cwd: projectRoot,
      encoding: 'utf-8'
    })
    return true
  } catch (err) {
    if (!silent) {
      console.error(`[postinstall] Command failed: ${command}`)
    }
    return false
  }
}

async function main() {
  log('Running postinstall scripts...')
  
  log('Installing electron-builder app dependencies...')
  runCommand('npx electron-builder install-app-deps')
  
  const venvPath = join(projectRoot, 'resources', 'python-venv')
  const requirementsPath = join(projectRoot, 'one_to_two_V2', 'requirements.txt')
  
  if (!existsSync(venvPath) && existsSync(requirementsPath)) {
    log('Python virtual environment not found.')
    log('To set up Python environment, run: npm run build:python')
  }
  
  log('Postinstall completed!')
}

main().catch(err => {
  console.error('[postinstall] Error:', err.message)
  process.exit(0)
})
