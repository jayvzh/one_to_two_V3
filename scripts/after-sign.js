import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

export default async function(context) {
  console.log('[after-sign] Build completed successfully!')
  
  console.log('[after-sign] Output directory:', context.outDir)
  console.log('[after-sign] Artifact paths:', context.artifactPaths)
  
  return true
}
