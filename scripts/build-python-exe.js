// scripts/build-python-exe.js
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { existsSync, statSync } from 'fs';

// 获取 ES 模块中的 __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const projectRoot = resolve(__dirname, '..');
const pythonApiDir = join(projectRoot, 'python-api');
const specFile = join(pythonApiDir, 'onetotwo-api.spec');
const distDir = join(projectRoot, 'dist');
const workPath = join(projectRoot, 'build', 'pyinstaller');
const pythonExe = process.platform === 'win32' ? 'python' : 'python3';

console.log('=== Building Python API executable with PyInstaller ===');
console.log('Project root:', projectRoot);
console.log('Python API dir:', pythonApiDir);
console.log('Spec file:', specFile);
console.log('Dist path:', distDir);
console.log('Work path:', workPath);

// 确保工作目录存在
import { mkdirSync } from 'fs';
try {
  mkdirSync(workPath, { recursive: true });
  mkdirSync(distDir, { recursive: true });
} catch (err) {
  // 目录可能已存在，继续
}

const pyinstallerCmd = `"${pythonExe}" -m PyInstaller "${specFile}" --noconfirm --clean --log-level WARN --distpath "${distDir}" --workpath "${workPath}"`;

console.log('Running:', pyinstallerCmd);

try {
  execSync(pyinstallerCmd, {
    cwd: projectRoot,
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
    },
  });
  console.log('\n=== Python API build completed successfully! ===');
  
  const exePath = join(distDir, 'onetotwo-api.exe');
  if (existsSync(exePath)) {
    const stats = statSync(exePath);
    const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
    console.log(`Output: ${exePath}`);
    console.log(`Size: ${sizeMB} MB`);
  } else {
    // 尝试查找其他可能的输出文件名
    console.log('Checking for output files in dist directory...');
    const files = readdirSync(distDir);
    console.log('Files in dist:', files);
  }
} catch (error) {
  console.error('\n=== Python API build failed! ===');
  console.error(error.message);
  process.exit(1);
}