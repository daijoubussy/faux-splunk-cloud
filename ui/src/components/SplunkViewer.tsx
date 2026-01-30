import { useState } from 'react';
import {
  ArrowTopRightOnSquareIcon,
  ComputerDesktopIcon,
  XMarkIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

type ViewMode = 'new-tab' | 'embed' | 'guacamole';

interface SplunkViewerProps {
  webUrl: string;
  instanceId: string;
  instanceName: string;
  guacamoleUrl?: string;
}

export function SplunkViewer({
  webUrl,
  instanceId: _instanceId,
  instanceName,
  guacamoleUrl,
}: SplunkViewerProps) {
  // _instanceId is available for future use (e.g., logging, analytics)
  const [viewMode, setViewMode] = useState<ViewMode>('new-tab');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showEmbed, setShowEmbed] = useState(false);

  const handleOpenNewTab = () => {
    window.open(webUrl, '_blank', 'noopener,noreferrer');
  };

  const handleEmbed = () => {
    setShowEmbed(true);
    setViewMode('embed');
  };

  const handleGuacamole = () => {
    if (guacamoleUrl) {
      setShowEmbed(true);
      setViewMode('guacamole');
    }
  };

  const handleCloseEmbed = () => {
    setShowEmbed(false);
    setIsFullscreen(false);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div className="space-y-4">
      {/* View Options */}
      <div className="bg-splunk-green/10 border border-splunk-green rounded-lg p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="font-medium text-gray-900">Splunk is Ready!</h3>
            <p className="text-sm text-gray-600">Choose how to access your Splunk instance</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleOpenNewTab}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-splunk-green hover:bg-green-600"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-2" />
              Open in New Tab
            </button>
            <button
              onClick={handleEmbed}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <ComputerDesktopIcon className="h-4 w-4 mr-2" />
              Embed View
            </button>
            {guacamoleUrl && (
              <button
                onClick={handleGuacamole}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                title="Remote Desktop via Guacamole"
              >
                <ComputerDesktopIcon className="h-4 w-4 mr-2" />
                Remote Desktop
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Embedded View */}
      {showEmbed && (
        <div
          className={clsx(
            'bg-white border border-gray-200 rounded-lg overflow-hidden',
            isFullscreen
              ? 'fixed inset-0 z-50 rounded-none'
              : 'relative'
          )}
        >
          {/* Embed Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-900 text-white">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <span className="text-sm font-medium">
                {instanceName} - {viewMode === 'guacamole' ? 'Remote Desktop' : 'Splunk Web'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleFullscreen}
                className="p-1.5 hover:bg-gray-700 rounded"
                title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
              >
                {isFullscreen ? (
                  <ArrowsPointingInIcon className="h-4 w-4" />
                ) : (
                  <ArrowsPointingOutIcon className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={handleOpenNewTab}
                className="p-1.5 hover:bg-gray-700 rounded"
                title="Open in New Tab"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              </button>
              <button
                onClick={handleCloseEmbed}
                className="p-1.5 hover:bg-gray-700 rounded"
                title="Close"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Iframe Content */}
          <div className={clsx(isFullscreen ? 'h-[calc(100vh-48px)]' : 'h-[600px]')}>
            {viewMode === 'guacamole' && guacamoleUrl ? (
              <iframe
                src={guacamoleUrl}
                className="w-full h-full border-0"
                title={`Guacamole - ${instanceName}`}
                allow="clipboard-read; clipboard-write"
              />
            ) : (
              <iframe
                src={webUrl}
                className="w-full h-full border-0"
                title={`Splunk Web - ${instanceName}`}
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
              />
            )}
          </div>

          {/* Connection Note */}
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
            {viewMode === 'guacamole' ? (
              <span>Connected via Apache Guacamole (VNC/RDP)</span>
            ) : (
              <span>
                Note: Some features may not work in embedded mode due to browser security restrictions.
                Use "Open in New Tab" for full functionality.
              </span>
            )}
          </div>
        </div>
      )}

      {/* Guacamole Setup Info (if not configured) */}
      {!guacamoleUrl && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-800">Remote Desktop Access</h4>
          <p className="mt-1 text-sm text-blue-700">
            For a better embedded experience with full mouse/keyboard support, configure
            Apache Guacamole for VNC/RDP access to your Splunk instances.
          </p>
          <a
            href="https://guacamole.apache.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-sm text-blue-600 hover:underline"
          >
            Learn more about Apache Guacamole →
          </a>
        </div>
      )}
    </div>
  );
}

export default SplunkViewer;
