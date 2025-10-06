#!/usr/bin/env node

/**
 * Cross-platform installer builder for AI Assistant Desktop
 * Builds installers for Windows, macOS, and Linux
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const platform = process.platform;
const arch = process.arch;

console.log(`🚀 Building AI Assistant Desktop for ${platform}-${arch}`);

// Configuration
const config = {
  appName: 'AI Assistant',
  appId: 'com.aiassistant.desktop',
  version: '1.0.0',
  description: 'AI Assistant Desktop Application - Your Personal AI Employee',
  author: 'AI Assistant Team',
  homepage: 'https://github.com/ai-assistant/desktop',
  buildDir: 'dist',
  releaseDir: 'release',
  platforms: {
    win32: {
      target: 'nsis',
      icon: 'assets/icons/icon.ico',
      artifactName: '${productName}-Setup-${version}.${ext}'
    },
    darwin: {
      target: 'dmg',
      icon: 'assets/icons/icon.icns',
      artifactName: '${productName}-${version}.${ext}'
    },
    linux: {
      target: ['AppImage', 'deb', 'rpm'],
      icon: 'assets/icons/icon.png',
      artifactName: '${productName}-${version}-${arch}.${ext}'
    }
  }
};

// Ensure directories exist
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// Execute command with error handling
function exec(command, options = {}) {
  try {
    console.log(`📦 Executing: ${command}`);
    return execSync(command, { 
      stdio: 'inherit', 
      cwd: process.cwd(),
      ...options 
    });
  } catch (error) {
    console.error(`❌ Command failed: ${command}`);
    console.error(error.message);
    process.exit(1);
  }
}

// Install dependencies
function installDependencies() {
  console.log('📥 Installing dependencies...');
  
  // Install backend dependencies
  console.log('🐍 Installing Python dependencies...');
  exec('pip install -r backend/requirements.txt');
  
  // Install frontend dependencies
  console.log('📦 Installing Node.js dependencies...');
  exec('npm install');
  exec('cd frontend && npm install');
}

// Build the application
function buildApplication() {
  console.log('🔨 Building application...');
  
  // Build frontend
  console.log('⚛️ Building React frontend...');
  exec('cd frontend && npm run build');
  
  // Copy backend files
  console.log('🐍 Preparing backend files...');
  ensureDir('frontend/dist/backend');
  exec('cp -r backend/* frontend/dist/backend/', { shell: true });
  
  // Create startup script
  createStartupScript();
}

// Create platform-specific startup script
function createStartupScript() {
  const isWindows = platform === 'win32';
  const scriptExt = isWindows ? '.bat' : '.sh';
  const scriptName = `start-backend${scriptExt}`;
  
  let scriptContent;
  
  if (isWindows) {
    scriptContent = `@echo off
cd /d "%~dp0backend"
python main.py
`;
  } else {
    scriptContent = `#!/bin/bash
cd "$(dirname "$0")/backend"
python3 main.py
`;
  }
  
  fs.writeFileSync(path.join('frontend/dist', scriptName), scriptContent);
  
  if (!isWindows) {
    exec(`chmod +x frontend/dist/${scriptName}`);
  }
}

// Build installers
function buildInstallers() {
  console.log('📦 Building installers...');
  
  // Ensure release directory exists
  ensureDir(config.releaseDir);
  
  // Create electron-builder config
  createElectronBuilderConfig();
  
  // Build for current platform
  exec('cd frontend && npm run dist');
  
  console.log('✅ Build completed successfully!');
  console.log(`📁 Installers available in: frontend/release/`);
}

// Create electron-builder configuration
function createElectronBuilderConfig() {
  const builderConfig = {
    appId: config.appId,
    productName: config.appName,
    directories: {
      output: 'release',
      buildResources: '../assets'
    },
    files: [
      'dist/**/*',
      'node_modules/**/*',
      'package.json'
    ],
    extraResources: [
      {
        from: '../backend',
        to: 'backend',
        filter: ['**/*', '!**/__pycache__', '!**/*.pyc', '!**/tests']
      },
      {
        from: '../assets',
        to: 'assets'
      }
    ],
    win: {
      target: config.platforms.win32.target,
      icon: config.platforms.win32.icon,
      artifactName: config.platforms.win32.artifactName,
      publisherName: config.author,
      requestedExecutionLevel: 'asInvoker'
    },
    nsis: {
      oneClick: false,
      allowToChangeInstallationDirectory: true,
      createDesktopShortcut: true,
      createStartMenuShortcut: true,
      shortcutName: config.appName
    },
    mac: {
      target: config.platforms.darwin.target,
      icon: config.platforms.darwin.icon,
      artifactName: config.platforms.darwin.artifactName,
      category: 'public.app-category.productivity',
      hardenedRuntime: true,
      entitlements: 'build/entitlements.mac.plist',
      entitlementsInherit: 'build/entitlements.mac.plist'
    },
    dmg: {
      title: `${config.appName} ${config.version}`,
      icon: config.platforms.darwin.icon,
      background: 'assets/dmg-background.png',
      contents: [
        {
          x: 130,
          y: 220
        },
        {
          x: 410,
          y: 220,
          type: 'link',
          path: '/Applications'
        }
      ]
    },
    linux: {
      target: config.platforms.linux.target,
      icon: config.platforms.linux.icon,
      artifactName: config.platforms.linux.artifactName,
      category: 'Office',
      synopsis: config.description
    },
    appImage: {
      license: 'LICENSE'
    },
    deb: {
      depends: ['python3', 'python3-pip'],
      priority: 'optional'
    },
    rpm: {
      depends: ['python3', 'python3-pip']
    },
    publish: null
  };
  
  // Write config to frontend directory
  fs.writeFileSync(
    path.join('frontend', 'electron-builder.json'),
    JSON.stringify(builderConfig, null, 2)
  );
}

// Create portable version
function createPortable() {
  console.log('📦 Creating portable version...');
  
  const portableDir = path.join(config.releaseDir, 'portable');
  ensureDir(portableDir);
  
  // Copy built application
  exec(`cp -r frontend/dist/* ${portableDir}/`, { shell: true });
  
  // Create portable launcher
  const launcherContent = platform === 'win32' 
    ? `@echo off
start "" "AI Assistant.exe"
start /b start-backend.bat
`
    : `#!/bin/bash
./ai-assistant &
./start-backend.sh &
`;
  
  const launcherName = platform === 'win32' ? 'launch.bat' : 'launch.sh';
  fs.writeFileSync(path.join(portableDir, launcherName), launcherContent);
  
  if (platform !== 'win32') {
    exec(`chmod +x ${path.join(portableDir, launcherName)}`);
  }
  
  console.log(`✅ Portable version created in: ${portableDir}`);
}

// Main build process
function main() {
  const args = process.argv.slice(2);
  const buildType = args[0] || 'all';
  
  console.log(`🎯 Build type: ${buildType}`);
  
  try {
    if (buildType === 'deps' || buildType === 'all') {
      installDependencies();
    }
    
    if (buildType === 'build' || buildType === 'all') {
      buildApplication();
    }
    
    if (buildType === 'installer' || buildType === 'all') {
      buildInstallers();
    }
    
    if (buildType === 'portable' || buildType === 'all') {
      createPortable();
    }
    
    console.log('🎉 All builds completed successfully!');
    
    // Show build artifacts
    console.log('\n📋 Build Artifacts:');
    console.log(`   Installers: frontend/release/`);
    console.log(`   Portable:   ${config.releaseDir}/portable/`);
    
  } catch (error) {
    console.error('❌ Build failed:', error.message);
    process.exit(1);
  }
}

// Handle command line arguments
if (require.main === module) {
  main();
}

module.exports = {
  buildApplication,
  buildInstallers,
  createPortable,
  config
};