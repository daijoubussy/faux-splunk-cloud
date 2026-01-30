/**
 * Wrapper component that provides Splunk theme context to child components.
 */

import React from 'react';
import { SplunkThemeProvider } from '@splunk/themes';

interface SplunkThemedContentProps {
  children: React.ReactNode;
  colorScheme?: 'light' | 'dark';
  family?: 'enterprise' | 'prisma';
  density?: 'comfortable' | 'compact';
}

export function SplunkThemedContent({
  children,
  colorScheme = 'light',
  family = 'enterprise',
  density = 'comfortable',
}: SplunkThemedContentProps) {
  return (
    <SplunkThemeProvider
      family={family}
      colorScheme={colorScheme}
      density={density}
    >
      {children}
    </SplunkThemeProvider>
  );
}

export default SplunkThemedContent;
