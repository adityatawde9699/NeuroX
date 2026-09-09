import '@testing-library/jest-dom/vitest'
import { beforeEach } from 'vitest'

// Provide a minimal localStorage for tests running in happy-dom.
// happy-dom includes localStorage, but this ensures the key used
// by authStorage.ts is always clean between test files.
beforeEach(() => {
  localStorage.clear()
})
