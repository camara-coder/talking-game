/**
 * Testing utilities and helpers
 */
import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { GameState } from '../types';

// Custom render function with providers
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { ...options });
}

// Mock WebSocket factory
export function createMockWebSocket() {
  const listeners: { [key: string]: Function[] } = {};

  return {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn((event: string, callback: Function) => {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(callback);
    }),
    removeEventListener: jest.fn((event: string, callback: Function) => {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((cb) => cb !== callback);
      }
    }),
    readyState: WebSocket.OPEN,
    trigger: (event: string, data?: any) => {
      if (listeners[event]) {
        listeners[event].forEach((callback) => {
          callback(data || { data: JSON.stringify({}) });
        });
      }
    },
  };
}

// Mock AudioContext factory
export function createMockAudioContext() {
  return {
    createBufferSource: jest.fn().mockReturnValue({
      buffer: null,
      connect: jest.fn(),
      start: jest.fn(),
      stop: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      onended: null,
    }),
    createGain: jest.fn().mockReturnValue({
      gain: { value: 1, setValueAtTime: jest.fn() },
      connect: jest.fn(),
    }),
    decodeAudioData: jest.fn().mockResolvedValue({
      duration: 1.5,
      length: 36000,
      numberOfChannels: 1,
      sampleRate: 24000,
      getChannelData: jest.fn(() => new Float32Array(36000)),
    }),
    destination: {},
    state: 'running',
    close: jest.fn().mockResolvedValue(undefined),
  };
}

// Mock VoiceServiceAPI
export function createMockVoiceServiceAPI() {
  return {
    startSession: jest.fn().mockResolvedValue({
      session_id: 'test-session-123',
      status: 'listening',
    }),
    stopSession: jest.fn().mockResolvedValue({
      session_id: 'test-session-123',
      status: 'processing',
    }),
    getHealth: jest.fn().mockResolvedValue({
      service: 'healthy',
      timestamp: new Date().toISOString(),
    }),
    getSession: jest.fn().mockResolvedValue({
      session_id: 'test-session-123',
      status: 'idle',
      turns: [],
    }),
  };
}

// Mock VoiceWebSocketClient
export function createMockWebSocketClient() {
  const callbacks: { [key: string]: Function[] } = {};

  return {
    connect: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    on: jest.fn((event: string, callback: Function) => {
      if (!callbacks[event]) callbacks[event] = [];
      callbacks[event].push(callback);
    }),
    off: jest.fn((event: string, callback: Function) => {
      if (callbacks[event]) {
        callbacks[event] = callbacks[event].filter((cb) => cb !== callback);
      }
    }),
    trigger: (event: string, data?: any) => {
      if (callbacks[event]) {
        callbacks[event].forEach((callback) => callback(data));
      }
    },
  };
}

// Test data factories
export const createTestSessionStartResponse = (overrides = {}) => ({
  session_id: 'test-session-123',
  status: 'listening' as const,
  ...overrides,
});

export const createTestWebSocketEvent = (type: string, payload: any) => ({
  type,
  session_id: 'test-session-123',
  turn_id: 'test-turn-123',
  ts: new Date().toISOString(),
  payload,
});

export const createTestStateEvent = (state: GameState) =>
  createTestWebSocketEvent('state', { state });

export const createTestTranscriptEvent = (text: string, partial = false) =>
  createTestWebSocketEvent(partial ? 'transcript.partial' : 'transcript.final', {
    text,
  });

export const createTestReplyTextEvent = (text: string) =>
  createTestWebSocketEvent('reply.text', { text });

export const createTestAudioReadyEvent = (url: string, duration_ms = 1500) =>
  createTestWebSocketEvent('reply.audio_ready', {
    url,
    duration_ms,
    format: 'wav',
    sample_rate_hz: 24000,
    channels: 1,
  });

export const createTestErrorEvent = (code: string, message: string) =>
  createTestWebSocketEvent('error', { code, message });

// Wait utilities
export const waitFor = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms));

// Re-export everything from testing library
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
