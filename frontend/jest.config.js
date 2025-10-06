/** @type {import('jest').Config} */
module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Setup files
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  
  // Module name mapping
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/components/(.*)$': '<rootDir>/src/renderer/components/$1',
    '^@/services/(.*)$': '<rootDir>/src/renderer/services/$1',
    '^@/contexts/(.*)$': '<rootDir>/src/renderer/contexts/$1',
    '^@/hooks/(.*)$': '<rootDir>/src/renderer/hooks/$1',
    '^@/utils/(.*)$': '<rootDir>/src/renderer/utils/$1',
    '^@/types/(.*)$': '<rootDir>/src/renderer/types/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': 
      '<rootDir>/src/__mocks__/fileMock.js',
  },
  
  // File extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  
  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  
  // Test match patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js|jsx)',
    '<rootDir>/src/**/*.(test|spec).(ts|tsx|js|jsx)',
  ],
  
  // Coverage configuration
  collectCoverageFrom: [
    'src/renderer/**/*.{ts,tsx}',
    '!src/renderer/**/*.d.ts',
    '!src/renderer/index.tsx',
    '!src/renderer/**/__tests__/**',
    '!src/renderer/**/*.test.{ts,tsx}',
    '!src/renderer/**/*.spec.{ts,tsx}',
  ],
  
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json'],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
  
  // Module paths to ignore
  modulePathIgnorePatterns: ['<rootDir>/dist/', '<rootDir>/node_modules/'],
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Restore mocks after each test
  restoreMocks: true,
  
  // Verbose output
  verbose: true,
  
  // Test timeout
  testTimeout: 10000,
  
  // Error handling
  errorOnDeprecated: true,
  
  // Transform configuration
  preset: 'ts-jest',
  
  // Performance monitoring
  maxWorkers: '50%',
};