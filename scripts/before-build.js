import { existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

export default async function(context) {
  console.log('[before-build] Running pre-build checks...')
  
  const outDir = join(projectRoot, 'out')
  if (!existsSync(outDir)) {
    throw new Error('Build output directory not found. Run "npm run build" first.')
  }
  
  const pythonApiDir = join(projectRoot, 'python-api')
  if (!existsSync(pythonApiDir)) {
    throw new Error('Python API directory not found.')
  }
  
  const configDir = join(projectRoot, 'config')
  if (!existsSync(configDir)) {
    throw new Error('config directory not found.')
  }
  
  console.log('[before-build] Pre-build checks passed.')
  return true
}
