# Splunk UI Component Migration Plan

## Overview

This document outlines the migration from the current Tailwind CSS-based React UI to Splunk UI components (`@splunk/react-ui`). **No custom CSS will be used** - all styling will come from Splunk's component library and theme system.

## Current State vs Target State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CURRENT STATE                      TARGET STATE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  React + Tailwind CSS         →     React + @splunk/react-ui               │
│  Custom StatusBadge           →     <Badge appearance="success" />         │
│  <input className="...">      →     <TextInput label="..." />              │
│  <table className="...">      →     <Table columns={} rows={} />           │
│  Custom navigation            →     <SidePanel> + <Menu>                   │
│  Headless UI modals           →     <Modal open={} onClose={} />           │
│  Tailwind colors              →     @splunk/themes variables               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dependencies

```json
{
  "dependencies": {
    "@splunk/react-ui": "^5.6.0",
    "@splunk/themes": "^1.4.1",
    "@splunk/styled-components": "^1.0.0",
    "styled-components": "^5.3.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  }
}
```

## Remove These Dependencies

```json
{
  "devDependencies": {
    "tailwindcss": "REMOVE",
    "autoprefixer": "REMOVE",
    "postcss": "REMOVE",
    "@headlessui/react": "REMOVE"
  }
}
```

## Files to Delete

```
ui/
├── tailwind.config.js      # DELETE
├── postcss.config.js       # DELETE
├── src/
│   └── index.css           # DELETE (Tailwind directives)
```

---

## Component Migration Matrix

### Buttons & Actions

| Current | Splunk UI | Migration Notes |
|---------|-----------|-----------------|
| `<button className="bg-splunk-green...">` | `<Button appearance="primary">` | Use `appearance` prop |
| `<button className="bg-red-600...">` | `<Button appearance="destructive">` | For delete actions |
| `<button className="border-gray...">` | `<Button appearance="secondary">` | Default style |
| Disabled state via className | `disabled` prop | Native support |

**Before:**
```tsx
<button
  className="inline-flex items-center px-4 py-2 border border-transparent
             text-sm font-medium rounded-md shadow-sm text-white
             bg-splunk-green hover:bg-green-600 disabled:opacity-50"
  disabled={isLoading}
>
  Create Instance
</button>
```

**After:**
```tsx
import { Button } from '@splunk/react-ui/Button';

<Button
  appearance="primary"
  disabled={isLoading}
  onClick={handleCreate}
>
  Create Instance
</Button>
```

### Form Inputs

| Current | Splunk UI | Migration Notes |
|---------|-----------|-----------------|
| `<input type="text">` | `<TextInput />` | Includes label support |
| `<textarea>` | `<TextArea />` | With resize control |
| `<select>` | `<Select />` | Rich option rendering |
| `<input type="checkbox">` | `<Checkbox />` | Proper accessibility |
| `<input type="radio">` | `<Radio />` | Group support |

**Before:**
```tsx
<div>
  <label className="block text-sm font-medium text-gray-700">
    Instance Name
  </label>
  <input
    type="text"
    value={name}
    onChange={(e) => setName(e.target.value)}
    placeholder="my-splunk-instance"
    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm
               focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
  />
</div>
```

**After:**
```tsx
import { TextInput } from '@splunk/react-ui/TextInput';

<TextInput
  label="Instance Name"
  value={name}
  onChange={(e, { value }) => setName(value)}
  placeholder="my-splunk-instance"
  help="Lowercase letters, numbers, and hyphens only"
/>
```

### Status Badges

| Current | Splunk UI | Appearance Value |
|---------|-----------|------------------|
| `bg-green-100 text-green-800` | `appearance="success"` | Running |
| `bg-yellow-100 text-yellow-800` | `appearance="warning"` | Starting/Stopping |
| `bg-red-100 text-red-800` | `appearance="error"` | Error |
| `bg-gray-100 text-gray-800` | `appearance="default"` | Stopped |
| `bg-blue-100 text-blue-800` | `appearance="info"` | Provisioning |

**Before:**
```tsx
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    starting: 'bg-yellow-100 text-yellow-800 animate-pulse',
    stopped: 'bg-gray-100 text-gray-800',
    error: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${colors[status]}`}>
      {status}
    </span>
  );
}
```

**After:**
```tsx
import { Badge } from '@splunk/react-ui/Badge';

const appearanceMap: Record<string, string> = {
  running: 'success',
  starting: 'warning',
  stopped: 'default',
  error: 'error',
  provisioning: 'info',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      appearance={appearanceMap[status] || 'default'}
      label={status}
    />
  );
}
```

### Tables

**Before:**
```tsx
<table className="min-w-full divide-y divide-gray-200">
  <thead className="bg-gray-50">
    <tr>
      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Name</th>
      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Status</th>
    </tr>
  </thead>
  <tbody className="bg-white divide-y divide-gray-200">
    {instances.map((instance) => (
      <tr key={instance.id}>
        <td className="px-6 py-4">{instance.name}</td>
        <td className="px-6 py-4"><StatusBadge status={instance.status} /></td>
      </tr>
    ))}
  </tbody>
</table>
```

**After:**
```tsx
import { Table } from '@splunk/react-ui/Table';

const columns = [
  { key: 'name', label: 'Name', sortable: true },
  {
    key: 'status',
    label: 'Status',
    render: (value: string) => <StatusBadge status={value} />
  },
];

<Table
  columns={columns}
  rows={instances}
  rowKey="id"
  stripeRows
/>
```

### Navigation

**Before:**
```tsx
<div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
  <div className="flex min-h-0 flex-1 flex-col bg-gray-900">
    <nav className="mt-8 flex-1 space-y-1 px-2">
      {navigation.map((item) => (
        <NavLink
          key={item.name}
          to={item.href}
          className={clsx(
            isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-700',
            'group flex items-center px-3 py-2 text-sm font-medium rounded-md'
          )}
        >
          <item.icon className="mr-3 h-5 w-5" />
          {item.name}
        </NavLink>
      ))}
    </nav>
  </div>
</div>
```

**After:**
```tsx
import { SidePanel } from '@splunk/react-ui/SidePanel';
import { Menu, MenuItem } from '@splunk/react-ui/Menu';

<SidePanel>
  <Menu>
    {navigation.map((item) => (
      <MenuItem
        key={item.name}
        to={item.href}
        selected={isActive}
        icon={<item.icon />}
      >
        {item.name}
      </MenuItem>
    ))}
  </Menu>
</SidePanel>
```

### Modals

**Before:**
```tsx
// Using Headless UI Dialog
<Dialog open={isOpen} onClose={setIsOpen}>
  <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
  <div className="fixed inset-0 flex items-center justify-center p-4">
    <Dialog.Panel className="mx-auto max-w-sm rounded bg-white p-6">
      <Dialog.Title className="text-lg font-medium">Confirm Delete</Dialog.Title>
      {/* content */}
    </Dialog.Panel>
  </div>
</Dialog>
```

**After:**
```tsx
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@splunk/react-ui/Modal';
import { Button } from '@splunk/react-ui/Button';

<Modal open={isOpen} onClose={() => setIsOpen(false)}>
  <ModalHeader title="Confirm Delete" />
  <ModalBody>
    Are you sure you want to delete this instance?
  </ModalBody>
  <ModalFooter>
    <Button appearance="secondary" onClick={() => setIsOpen(false)}>
      Cancel
    </Button>
    <Button appearance="destructive" onClick={handleDelete}>
      Delete
    </Button>
  </ModalFooter>
</Modal>
```

### Cards/Panels

**Before:**
```tsx
<div className="bg-white shadow rounded-lg overflow-hidden">
  <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
    <h3 className="text-lg font-medium text-gray-900">Instance Details</h3>
  </div>
  <div className="px-4 py-5 sm:px-6">
    {/* content */}
  </div>
</div>
```

**After:**
```tsx
import { Card, CardHeader, CardBody } from '@splunk/react-ui/Card';

<Card>
  <CardHeader title="Instance Details" />
  <CardBody>
    {/* content */}
  </CardBody>
</Card>
```

---

## Theme Setup

### Main Entry Point (main.tsx)

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { SplunkThemeProvider } from '@splunk/themes/SplunkThemeProvider';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SplunkThemeProvider family="enterprise" colorScheme="light" density="compact">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </SplunkThemeProvider>
  </React.StrictMode>
);
```

### Theme Variables Access

```tsx
import styled from 'styled-components';
import { variables } from '@splunk/themes';

// Use theme variables instead of Tailwind classes
const Container = styled.div`
  background: ${variables.backgroundColor};
  color: ${variables.textColor};
  padding: ${variables.spacing.md};
  border-radius: ${variables.borderRadius};
`;
```

---

## Migration Order

### Phase 1: Infrastructure (Week 1)
1. [ ] Install Splunk UI dependencies
2. [ ] Remove Tailwind dependencies
3. [ ] Delete Tailwind config files
4. [ ] Set up SplunkThemeProvider in main.tsx
5. [ ] Create StatusBadge component with Splunk Badge

### Phase 2: Core Components (Week 2)
6. [ ] Migrate buttons across all pages
7. [ ] Migrate form inputs (TextInput, Select, Checkbox)
8. [ ] Migrate tables to Splunk Table component
9. [ ] Migrate navigation to SidePanel + Menu

### Phase 3: Pages (Week 3)
10. [ ] Migrate Dashboard.tsx
11. [ ] Migrate Instances.tsx
12. [ ] Migrate CreateInstance.tsx
13. [ ] Migrate InstanceDetail.tsx

### Phase 4: Attack Simulation Pages (Week 4)
14. [ ] Migrate Attacks.tsx
15. [ ] Migrate ThreatActors.tsx
16. [ ] Migrate Campaigns.tsx
17. [ ] Migrate CampaignDetail.tsx
18. [ ] Migrate Scenarios.tsx

### Phase 5: Final (Week 5)
19. [ ] Migrate AcsExplorer.tsx
20. [ ] Remove all remaining Tailwind classes
21. [ ] Verify dark mode works
22. [ ] Visual regression testing

---

## Backstage Integration Notes

When integrating with Backstage, wrap Splunk components appropriately:

```tsx
// In Backstage plugin
import { SplunkThemeProvider } from '@splunk/themes/SplunkThemeProvider';
import { useTheme } from '@backstage/core-plugin-api';

export const FauxSplunkPage = () => {
  const backstageTheme = useTheme();
  const colorScheme = backstageTheme.palette.mode === 'dark' ? 'dark' : 'light';

  return (
    <SplunkThemeProvider family="prisma" colorScheme={colorScheme}>
      {/* Splunk UI components */}
    </SplunkThemeProvider>
  );
};
```

---

## File Changes Summary

| File | Action | Notes |
|------|--------|-------|
| `package.json` | Modify | Add Splunk deps, remove Tailwind |
| `tailwind.config.js` | Delete | No longer needed |
| `postcss.config.js` | Delete | No longer needed |
| `src/index.css` | Delete | Tailwind directives |
| `src/main.tsx` | Modify | Add SplunkThemeProvider |
| `src/App.tsx` | Modify | Use SidePanel, Menu |
| `src/pages/*.tsx` | Modify | Replace all Tailwind classes |

---

## Testing Checklist

- [ ] All buttons render correctly
- [ ] Form inputs accept and validate input
- [ ] Tables display data and sort works
- [ ] Navigation highlights active route
- [ ] Modals open and close properly
- [ ] Dark mode toggle works
- [ ] Mobile responsive (if applicable)
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
