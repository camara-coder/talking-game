# Testing Guide

This document describes the comprehensive testing suite for the Voice Conversational Kids Game.

## Table of Contents

- [Overview](#overview)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [E2E Testing](#e2e-testing)
- [Running Tests](#running-tests)
- [CI/CD](#cicd)
- [Writing Tests](#writing-tests)
- [Coverage Reports](#coverage-reports)

---

## Overview

The testing suite consists of three main layers:

1. **Backend Tests** (Python/pytest) - Unit and integration tests for the voice service
2. **Frontend Tests** (Jest/React Testing Library) - Component and integration tests for the React UI
3. **E2E Tests** (Playwright) - End-to-end tests simulating real user interactions

### Test Coverage Goals

- **Backend**: >70% code coverage
- **Frontend**: >70% code coverage
- **E2E**: Critical user flows covered

---

## Backend Testing

### Setup

```bash
cd voice_service

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Install application dependencies
pip install -r requirements.txt
```

### Test Structure

```
voice_service/tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── test_text_math.py       # Math processing tests
│   └── test_audio_utils.py     # Audio utilities tests
└── integration/                # Integration tests
    ├── test_api_endpoints.py   # API endpoint tests
    └── test_websocket.py       # WebSocket tests
```

### Running Backend Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit -v

# Run integration tests only
pytest tests/integration -v

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_text_math.py -v

# Run tests matching a pattern
pytest -k "test_math" -v

# Run tests with specific markers
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "not requires_ollama" -v
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.requires_ollama` - Tests requiring Ollama
- `@pytest.mark.requires_audio` - Tests requiring audio devices
- `@pytest.mark.websocket` - WebSocket tests

### Example: Writing a Backend Unit Test

```python
import pytest
from app.utils.text_math import parse_spoken_number

def test_parse_single_digit():
    """Test parsing single digit numbers"""
    assert parse_spoken_number("five") == 5
    assert parse_spoken_number("zero") == 0
    assert parse_spoken_number("nine") == 9
```

### Example: Writing a Backend Integration Test

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_start_session(client: TestClient):
    """Test starting a new session"""
    response = client.post(
        "/api/session/start",
        json={"language": "en", "mode": "ptt"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "listening"
```

---

## Frontend Testing

### Setup

```bash
cd web-client

# Install dependencies
npm install

# Install test dependencies (should already be in package.json)
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

### Test Structure

```
web-client/src/
├── test/
│   ├── setup.ts                # Jest setup
│   ├── utils.tsx               # Test utilities
│   └── __mocks__/              # Mocks
└── components/
    └── __tests__/              # Component tests
        ├── PushToTalkButton.test.tsx
        └── CaptionDisplay.test.tsx
```

### Running Frontend Tests

```bash
# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- PushToTalkButton.test.tsx

# Update snapshots
npm test -- -u
```

### Example: Writing a Component Test

```typescript
import React from 'react';
import { render, screen, userEvent } from '../../test/utils';
import PushToTalkButton from '../PushToTalkButton';

describe('PushToTalkButton', () => {
  it('renders with correct text', () => {
    render(
      <PushToTalkButton
        state="idle"
        onPress={jest.fn()}
        onRelease={jest.fn()}
      />
    );

    expect(screen.getByText('Push to Talk')).toBeInTheDocument();
  });

  it('calls onPress when clicked', async () => {
    const onPress = jest.fn();
    const user = userEvent.setup();

    render(
      <PushToTalkButton
        state="idle"
        onPress={onPress}
        onRelease={jest.fn()}
      />
    );

    await user.click(screen.getByRole('button'));
    expect(onPress).toHaveBeenCalled();
  });
});
```

---

## E2E Testing

### Setup

```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

### Test Structure

```
e2e/
└── voice-game.spec.ts          # E2E test scenarios
```

### Running E2E Tests

```bash
# Run all E2E tests
npx playwright test

# Run in UI mode (interactive)
npx playwright test --ui

# Run specific browser
npx playwright test --project=chromium
npx playwright test --project=webkit
npx playwright test --project="Mobile Safari"

# Run in headed mode (see browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug

# Generate test report
npx playwright show-report
```

### Example: Writing an E2E Test

```typescript
import { test, expect } from '@playwright/test';

test('should display main UI elements', async ({ page }) => {
  await page.goto('/');

  // Check for character canvas
  const canvas = page.locator('canvas');
  await expect(canvas).toBeVisible();

  // Check for push-to-talk button
  const button = page.locator('button:has-text("Push to Talk")');
  await expect(button).toBeVisible();
});
```

---

## Running Tests

### Quick Commands

#### Backend Only
```bash
cd voice_service && pytest
```

#### Frontend Only
```bash
cd web-client && npm test
```

#### E2E Only
```bash
npx playwright test
```

#### All Tests
```bash
# From project root
npm run test:all
```

### Test Scripts

Add these to root `package.json`:

```json
{
  "scripts": {
    "test:backend": "cd voice_service && pytest",
    "test:frontend": "cd web-client && npm test",
    "test:e2e": "playwright test",
    "test:all": "npm run test:backend && npm run test:frontend && npm run test:e2e",
    "test:watch": "cd web-client && npm test -- --watch"
  }
}
```

---

## CI/CD

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

### Workflow Jobs

1. **Backend Tests** - Runs on Python 3.11 and 3.12
2. **Frontend Tests** - Runs on Node.js 18 and 20
3. **E2E Tests** - Full stack integration with Ollama
4. **Code Quality** - Linting and formatting checks
5. **Security Scan** - Trivy vulnerability scanning

### Viewing Results

- GitHub Actions tab shows test results
- Coverage reports uploaded to Codecov
- Playwright reports uploaded as artifacts

---

## Writing Tests

### Best Practices

#### General
- Write descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests focused and independent
- Mock external dependencies
- Use fixtures for common setup

#### Backend
- Test both success and error cases
- Use appropriate markers (@pytest.mark)
- Mock Ollama/STT/TTS in unit tests
- Test API contracts and response formats
- Verify error handling

#### Frontend
- Test user interactions, not implementation
- Use accessible queries (getByRole, getByLabelText)
- Test component behavior, not internal state
- Mock WebSocket and API calls
- Test edge cases (empty state, errors)

#### E2E
- Test critical user flows
- Keep tests stable and reliable
- Use appropriate waits and timeouts
- Test on multiple browsers/devices
- Include accessibility checks

### Test Coverage

#### What to Test

✅ **Do test:**
- Public APIs and interfaces
- User interactions and flows
- Error handling and edge cases
- Business logic and algorithms
- Integration points
- Accessibility features

❌ **Don't test:**
- Third-party libraries
- Framework internals
- Private implementation details
- Trivial getters/setters

---

## Coverage Reports

### Backend Coverage

```bash
cd voice_service
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html
```

### Frontend Coverage

```bash
cd web-client
npm test -- --coverage

# Open report
open coverage/lcov-report/index.html
```

### Coverage Thresholds

Configure in `pytest.ini` and `jest.config.js`:

```ini
# pytest.ini
[coverage:report]
fail_under = 70
```

```js
// jest.config.js
coverageThresholds: {
  global: {
    branches: 70,
    functions: 70,
    lines: 70,
    statements: 70,
  },
}
```

---

## Troubleshooting

### Common Issues

#### Backend Tests Fail Due to Missing Dependencies
```bash
# Install espeak-ng
sudo apt-get install espeak-ng

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio
```

#### Frontend Tests Fail with Canvas Errors
- Check `web-client/src/test/setup.ts` for canvas mock
- Ensure `jest.config.js` has correct transform settings

#### E2E Tests Timeout
```bash
# Increase timeout in playwright.config.ts
timeout: 60 * 1000,
```

#### WebSocket Tests Fail
- Ensure backend server is running
- Check WebSocket URL configuration
- Verify mock implementations

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [Jest Documentation](https://jestjs.io/)

---

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure tests pass locally
3. Maintain or improve coverage
4. Update this documentation if needed
5. Run full test suite before submitting PR

For questions or issues, please open a GitHub issue.
