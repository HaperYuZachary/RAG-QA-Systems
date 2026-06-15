import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const styleSource = readFileSync(new URL('./style.css', import.meta.url), 'utf8')

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styleSource.match(new RegExp(`${escapedSelector}\\s*\\{([\\s\\S]*?)\\}`))
  return match?.[1] ?? ''
}

test('desktop shell keeps the sidebar fixed while the main pane scrolls independently', () => {
  const sidebarRule = cssRule('.app-sidebar')
  const mainRule = cssRule('.app-main')
  const contentRule = cssRule('.app-content')

  assert.match(sidebarRule, /position:\s*fixed/)
  assert.match(sidebarRule, /height:\s*100dvh/)
  assert.match(sidebarRule, /overflow-y:\s*auto/)

  assert.match(mainRule, /margin-left:\s*var\(--sidebar-width\)/)
  assert.match(mainRule, /height:\s*100dvh/)
  assert.match(mainRule, /overflow-y:\s*auto/)

  assert.match(contentRule, /min-height:\s*calc\(100dvh - var\(--header-height\)\)/)
})

test('app shell uses a light frosted-glass sidebar instead of the old dark rail', () => {
  const sidebarRule = cssRule('.app-sidebar')
  const rootRule = cssRule(':root')

  assert.match(rootRule, /--sidebar-width:\s*292px/)
  assert.match(rootRule, /--glass-surface:/)
  assert.match(sidebarRule, /rgba\(255,\s*255,\s*255,/)
  assert.match(sidebarRule, /backdrop-filter:\s*saturate\(180%\)\s*blur/)
  assert.doesNotMatch(sidebarRule, /#0f172a/)
})

test('mobile shell returns the sidebar to document flow', () => {
  const mobileSection = styleSource.slice(styleSource.indexOf('@media (max-width: 900px)'))

  assert.match(mobileSection, /\.app-sidebar\s*\{[\s\S]*position:\s*relative/)
  assert.match(mobileSection, /\.app-main\s*\{[\s\S]*margin-left:\s*0/)
})
