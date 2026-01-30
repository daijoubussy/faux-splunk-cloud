/**
 * Main page component for Faux Splunk Cloud.
 *
 * Wraps content with Splunk theme provider and provides
 * routing for all sub-pages.
 */

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { SplunkThemeProvider } from '@splunk/themes/SplunkThemeProvider';
import {
  Content,
  Header,
  Page,
  TabbedLayout,
} from '@backstage/core-components';
import { useApi, configApiRef } from '@backstage/core-plugin-api';

// Import page components (lazy loaded)
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const InstancesPage = React.lazy(() => import('./pages/InstancesPage'));
const InstanceDetailPage = React.lazy(() => import('./pages/InstanceDetailPage'));
const AttacksPage = React.lazy(() => import('./pages/AttacksPage'));
const WorkflowsPage = React.lazy(() => import('./pages/WorkflowsPage'));
const AcsExplorerPage = React.lazy(() => import('./pages/AcsExplorerPage'));

/**
 * Wrapper that provides Splunk theming synchronized with Backstage.
 */
function SplunkThemedContent({ children }: { children: React.ReactNode }) {
  // Detect Backstage dark mode preference
  const config = useApi(configApiRef);
  const isDarkMode = config.getOptionalBoolean('app.darkMode') ?? false;

  return (
    <SplunkThemeProvider
      family="prisma"
      colorScheme={isDarkMode ? 'dark' : 'light'}
      density="compact"
    >
      {children}
    </SplunkThemeProvider>
  );
}

/**
 * Loading fallback for lazy-loaded pages.
 */
function PageLoader() {
  return (
    <Content>
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        Loading...
      </div>
    </Content>
  );
}

/**
 * Main page component with tabbed navigation.
 */
export function FauxSplunkCloudPage() {
  return (
    <SplunkThemedContent>
      <Page themeId="tool">
        <Header
          title="Faux Splunk Cloud"
          subtitle="Ephemeral Splunk Victoria instances for development & testing"
        />
        <TabbedLayout>
          <TabbedLayout.Route path="/" title="Dashboard">
            <React.Suspense fallback={<PageLoader />}>
              <DashboardPage />
            </React.Suspense>
          </TabbedLayout.Route>

          <TabbedLayout.Route path="/instances" title="Instances">
            <React.Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<InstancesPage />} />
                <Route path="/:instanceId" element={<InstanceDetailPage />} />
              </Routes>
            </React.Suspense>
          </TabbedLayout.Route>

          <TabbedLayout.Route path="/attacks" title="Attack Simulation">
            <React.Suspense fallback={<PageLoader />}>
              <AttacksPage />
            </React.Suspense>
          </TabbedLayout.Route>

          <TabbedLayout.Route path="/workflows" title="Workflows">
            <React.Suspense fallback={<PageLoader />}>
              <WorkflowsPage />
            </React.Suspense>
          </TabbedLayout.Route>

          <TabbedLayout.Route path="/acs" title="ACS Explorer">
            <React.Suspense fallback={<PageLoader />}>
              <AcsExplorerPage />
            </React.Suspense>
          </TabbedLayout.Route>
        </TabbedLayout>
      </Page>
    </SplunkThemedContent>
  );
}

export default FauxSplunkCloudPage;
