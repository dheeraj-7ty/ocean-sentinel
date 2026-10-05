import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock HTMLCanvasElement.getContext for Three.js in JSDOM
HTMLCanvasElement.prototype.getContext = vi.fn((type: string) => {
  if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {
    return {
      VERSION: 7938,
      getExtension: vi.fn(),
      getParameter: vi.fn((param) => {
        if (param === 7938 || param === undefined) return 'WebGL 1.0' // gl.VERSION
        if (param === 7937) return 'WebKit' // gl.RENDERER
        if (param === 7936) return 'WebKit' // gl.VENDOR
        return 2048
      }),
      createTexture: vi.fn(),
      bindTexture: vi.fn(),
      texParameteri: vi.fn(),
      texImage2D: vi.fn(),
      texImage3D: vi.fn(),
      clearColor: vi.fn(),
      clearDepth: vi.fn(),
      clear: vi.fn(),
      enable: vi.fn(),
      disable: vi.fn(),
      depthFunc: vi.fn(),
      frontFace: vi.fn(),
      cullFace: vi.fn(),
      viewport: vi.fn(),
      scissor: vi.fn(),
      createShader: vi.fn(),
      shaderSource: vi.fn(),
      compileShader: vi.fn(),
      getShaderPrecisionFormat: vi.fn(() => ({ precision: 23, rangeMin: 127, rangeMax: 127 })),
      getShaderParameter: vi.fn(() => true),
      getShaderInfoLog: vi.fn(() => ''),
      createProgram: vi.fn(),
      attachShader: vi.fn(),
      linkProgram: vi.fn(),
      getProgramParameter: vi.fn(() => true),
      getProgramInfoLog: vi.fn(() => ''),
      useProgram: vi.fn(),
      createBuffer: vi.fn(),
      bindBuffer: vi.fn(),
      bufferData: vi.fn(),
      enableVertexAttribArray: vi.fn(),
      vertexAttribPointer: vi.fn(),
      drawArrays: vi.fn(),
      drawElements: vi.fn(),
      createFramebuffer: vi.fn(),
      bindFramebuffer: vi.fn(),
      framebufferTexture2D: vi.fn(),
      createRenderbuffer: vi.fn(),
      bindRenderbuffer: vi.fn(),
      renderbufferStorage: vi.fn(),
      framebufferRenderbuffer: vi.fn(),
      checkFramebufferStatus: vi.fn(() => 36053), // gl.FRAMEBUFFER_COMPLETE
    }
  }
  return null
}) as any

// Mock window.requestAnimationFrame and cancelAnimationFrame
window.requestAnimationFrame = vi.fn((cb) => setTimeout(cb, 16) as any)
window.cancelAnimationFrame = vi.fn((id) => clearTimeout(id))

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any

// Mock EventSource for JSDOM
class MockEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  readyState = MockEventSource.OPEN
  url: string
  onopen: ((ev: any) => any) | null = null
  onmessage: ((ev: any) => any) | null = null
  onerror: ((ev: any) => any) | null = null
  constructor(url: string) {
    this.url = url
  }
  close() {
    this.readyState = MockEventSource.CLOSED
  }
}
;(globalThis as any).EventSource = MockEventSource as any
