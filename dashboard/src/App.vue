<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/companies', label: 'Firmen' },
  { path: '/leads', label: 'Leads' },
]
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="header-brand">MI Platform</div>
      <nav class="header-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
        >
          {{ item.label }}
        </router-link>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #1a1a2e;
}

.app {
  min-height: 100vh;
}

.header {
  background: #1a1a2e;
  color: white;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.header-brand {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.5px;
}

.header-nav {
  display: flex;
  gap: 4px;
}

.nav-link {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
}

.nav-link:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.router-link-active {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}

.main {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
