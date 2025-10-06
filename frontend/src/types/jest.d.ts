/**
 * Jest type definitions for AI Assistant Frontend
 */

import '@testing-library/jest-dom';

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R;
      toHaveClass(className: string): R;
      toHaveValue(value: string | number): R;
      toBeDisabled(): R;
      toBeEnabled(): R;
      toHaveFocus(): R;
      toHaveAttribute(attr: string, value?: string): R;
    }
  }

  // Jest globals
  const describe: jest.Describe;
  const it: jest.It;
  const test: jest.It;
  const expect: jest.Expect;
  const beforeAll: jest.Lifecycle;
  const beforeEach: jest.Lifecycle;
  const afterAll: jest.Lifecycle;
  const afterEach: jest.Lifecycle;
  const jest: Jest;

  // Global test utilities
  const global: NodeJS.Global & {
    testUtils: {
      createMockEvent: (type: string, properties?: any) => any;
      createMockFile: (name?: string, content?: string, type?: string) => File;
      waitFor: (ms?: number) => Promise<void>;
      flushPromises: () => Promise<void>;
    };
  };

  // Mock functions
  interface MockFunction<T extends (...args: any[]) => any> {
    (...args: Parameters<T>): ReturnType<T>;
    mockReturnValue(value: ReturnType<T>): this;
    mockResolvedValue(value: ReturnType<T>): this;
    mockRejectedValue(value: any): this;
    mockImplementation(fn: T): this;
    mockClear(): this;
    mockReset(): this;
    mockRestore(): this;
    mockReturnValueOnce(value: ReturnType<T>): this;
    mockResolvedValueOnce(value: ReturnType<T>): this;
    mockRejectedValueOnce(value: any): this;
    mockImplementationOnce(fn: T): this;
    toHaveBeenCalled(): void;
    toHaveBeenCalledTimes(times: number): void;
    toHaveBeenCalledWith(...args: Parameters<T>): void;
    toHaveBeenLastCalledWith(...args: Parameters<T>): void;
    toHaveBeenNthCalledWith(nthCall: number, ...args: Parameters<T>): void;
  }
}

export {};