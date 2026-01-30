import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BeakerIcon,
  ServerIcon,
  CircleStackIcon,
  KeyIcon,
  PlusIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';
import { instancesApi, createAcsApi } from '../api';

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 text-gray-400 hover:text-gray-600 rounded"
      title="Copy to clipboard"
    >
      {copied ? (
        <CheckIcon className="h-4 w-4 text-green-500" />
      ) : (
        <ClipboardDocumentIcon className="h-4 w-4" />
      )}
    </button>
  );
}

function IndexesPanel({ stackId }: { stackId: string }) {
  const queryClient = useQueryClient();
  const acsApi = useMemo(() => createAcsApi(stackId), [stackId]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newIndexName, setNewIndexName] = useState('');
  const [newIndexDatatype, setNewIndexDatatype] = useState<'event' | 'metric'>('event');
  const [newIndexSearchableDays, setNewIndexSearchableDays] = useState(90);

  const { data: indexes = [], isLoading, error } = useQuery({
    queryKey: ['acs-indexes', stackId],
    queryFn: acsApi.listIndexes,
  });

  const createMutation = useMutation({
    mutationFn: () => acsApi.createIndex(newIndexName, newIndexDatatype, newIndexSearchableDays),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['acs-indexes', stackId] });
      setShowCreateForm(false);
      setNewIndexName('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => acsApi.deleteIndex(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['acs-indexes', stackId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">Failed to load indexes</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Indexes</h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-white bg-splunk-green hover:bg-green-600"
        >
          <PlusIcon className="h-4 w-4 mr-1" />
          Create Index
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Index Name</label>
              <input
                type="text"
                value={newIndexName}
                onChange={(e) => setNewIndexName(e.target.value)}
                placeholder="my_index"
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Datatype</label>
              <select
                value={newIndexDatatype}
                onChange={(e) => setNewIndexDatatype(e.target.value as 'event' | 'metric')}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              >
                <option value="event">Event</option>
                <option value="metric">Metric</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Searchable Days</label>
              <input
                type="number"
                value={newIndexSearchableDays}
                onChange={(e) => setNewIndexSearchableDays(parseInt(e.target.value))}
                min={1}
                max={3650}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowCreateForm(false)}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => createMutation.mutate()}
              disabled={!newIndexName || createMutation.isPending}
              className="px-3 py-1.5 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-green-600 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
          {createMutation.isError && (
            <p className="text-sm text-red-600">Failed to create index. Please try again.</p>
          )}
        </div>
      )}

      {/* Indexes Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Datatype</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Searchable Days</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Events</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size (MB)</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {indexes.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No indexes found. Create one to get started.
                </td>
              </tr>
            ) : (
              indexes.map((index) => (
                <tr key={index.name} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center">
                      <CircleStackIcon className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-sm font-medium text-gray-900">{index.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{index.datatype}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{index.searchableDays}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{index.totalEventCount.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{index.totalRawSizeMB.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => deleteMutation.mutate(index.name)}
                      disabled={deleteMutation.isPending}
                      className="p-1 text-red-500 hover:text-red-700 rounded disabled:opacity-50"
                      title="Delete index"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HecTokensPanel({ stackId }: { stackId: string }) {
  const queryClient = useQueryClient();
  const acsApi = useMemo(() => createAcsApi(stackId), [stackId]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTokenName, setNewTokenName] = useState('');
  const [newTokenIndex, setNewTokenIndex] = useState('main');
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({});

  const { data: tokens = [], isLoading, error } = useQuery({
    queryKey: ['acs-hec-tokens', stackId],
    queryFn: acsApi.listHecTokens,
  });

  const createMutation = useMutation({
    mutationFn: () => acsApi.createHecToken(newTokenName, newTokenIndex),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['acs-hec-tokens', stackId] });
      setShowCreateForm(false);
      setNewTokenName('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => acsApi.deleteHecToken(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['acs-hec-tokens', stackId] });
    },
  });

  const toggleShowToken = (name: string) => {
    setShowTokens((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">Failed to load HEC tokens</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">HTTP Event Collector Tokens</h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-white bg-splunk-green hover:bg-green-600"
        >
          <PlusIcon className="h-4 w-4 mr-1" />
          Create Token
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Token Name</label>
              <input
                type="text"
                value={newTokenName}
                onChange={(e) => setNewTokenName(e.target.value)}
                placeholder="my_hec_token"
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Default Index</label>
              <input
                type="text"
                value={newTokenIndex}
                onChange={(e) => setNewTokenIndex(e.target.value)}
                placeholder="main"
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowCreateForm(false)}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => createMutation.mutate()}
              disabled={!newTokenName || createMutation.isPending}
              className="px-3 py-1.5 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-green-600 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
          {createMutation.isError && (
            <p className="text-sm text-red-600">Failed to create token. Please try again.</p>
          )}
        </div>
      )}

      {/* Tokens Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Token</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Default Index</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tokens.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No HEC tokens found. Create one to get started.
                </td>
              </tr>
            ) : (
              tokens.map((token) => (
                <tr key={token.name} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center">
                      <KeyIcon className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-sm font-medium text-gray-900">{token.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">
                        {showTokens[token.name] ? token.token : '••••••••••••••••'}
                      </code>
                      <button
                        onClick={() => toggleShowToken(token.name)}
                        className="p-1 text-gray-400 hover:text-gray-600 rounded"
                        title={showTokens[token.name] ? 'Hide token' : 'Show token'}
                      >
                        {showTokens[token.name] ? (
                          <EyeSlashIcon className="h-4 w-4" />
                        ) : (
                          <EyeIcon className="h-4 w-4" />
                        )}
                      </button>
                      <CopyButton text={token.token} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{token.defaultIndex}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                        token.disabled
                          ? 'bg-gray-100 text-gray-700'
                          : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {token.disabled ? 'Disabled' : 'Enabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => deleteMutation.mutate(token.name)}
                      disabled={deleteMutation.isPending}
                      className="p-1 text-red-500 hover:text-red-700 rounded disabled:opacity-50"
                      title="Delete token"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AcsExplorer() {
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'indexes' | 'hec'>('indexes');

  const { data: instances = [], isLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
  });

  const runningInstances = instances.filter((i) => i.status === 'running');
  const selectedInstanceData = instances.find((i) => i.id === selectedInstance);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">ACS API Explorer</h1>
        <p className="mt-1 text-sm text-gray-500">
          Interact with the Admin Config Service API for managing Splunk Cloud resources
        </p>
      </div>

      {/* Instance Selector */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center gap-4">
          <ServerIcon className="h-8 w-8 text-gray-400" />
          <div className="flex-1">
            <label htmlFor="instance-select" className="block text-sm font-medium text-gray-700 mb-1">
              Select Instance
            </label>
            <select
              id="instance-select"
              value={selectedInstance}
              onChange={(e) => setSelectedInstance(e.target.value)}
              className="block w-full max-w-md px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
            >
              <option value="">Choose a running instance...</option>
              {runningInstances.map((instance) => (
                <option key={instance.id} value={instance.id}>
                  {instance.name} ({instance.id})
                </option>
              ))}
            </select>
            {runningInstances.length === 0 && (
              <p className="mt-2 text-sm text-yellow-600">
                No running instances available. Create and start an instance first.
              </p>
            )}
          </div>
        </div>

        {selectedInstanceData && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 mb-2">ACS API Endpoint</h4>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-sm bg-white px-3 py-2 rounded border font-mono">
                {selectedInstanceData.endpoints.acs_url || `/{stack}/adminconfig/v2`}
              </code>
              <CopyButton text={selectedInstanceData.endpoints.acs_url || ''} />
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {selectedInstance ? (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('indexes')}
                className={`px-6 py-3 text-sm font-medium border-b-2 ${
                  activeTab === 'indexes'
                    ? 'border-splunk-green text-splunk-green'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <CircleStackIcon className="h-4 w-4 inline mr-2" />
                Indexes
              </button>
              <button
                onClick={() => setActiveTab('hec')}
                className={`px-6 py-3 text-sm font-medium border-b-2 ${
                  activeTab === 'hec'
                    ? 'border-splunk-green text-splunk-green'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <KeyIcon className="h-4 w-4 inline mr-2" />
                HEC Tokens
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'indexes' ? (
              <IndexesPanel stackId={selectedInstance} />
            ) : (
              <HecTokensPanel stackId={selectedInstance} />
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <BeakerIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Instance Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Select a running instance above to explore its ACS API.
          </p>
        </div>
      )}

      {/* API Documentation */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">ACS API Reference</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Indexes</h4>
            <ul className="space-y-1 text-sm text-gray-600">
              <li><code className="bg-gray-100 px-1 rounded">GET /{'{stack}'}/adminconfig/v2/indexes</code> - List indexes</li>
              <li><code className="bg-gray-100 px-1 rounded">POST /{'{stack}'}/adminconfig/v2/indexes</code> - Create index</li>
              <li><code className="bg-gray-100 px-1 rounded">DELETE /{'{stack}'}/adminconfig/v2/indexes/{'{name}'}</code> - Delete index</li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">HTTP Event Collector</h4>
            <ul className="space-y-1 text-sm text-gray-600">
              <li><code className="bg-gray-100 px-1 rounded">GET /{'{stack}'}/adminconfig/v2/inputs/http-event-collectors</code> - List tokens</li>
              <li><code className="bg-gray-100 px-1 rounded">POST /{'{stack}'}/adminconfig/v2/inputs/http-event-collectors</code> - Create token</li>
              <li><code className="bg-gray-100 px-1 rounded">DELETE /{'{stack}'}/adminconfig/v2/inputs/http-event-collectors/{'{name}'}</code> - Delete token</li>
            </ul>
          </div>
        </div>
        <p className="mt-4 text-sm text-gray-500">
          This API is compatible with the official Splunk Cloud Admin Config Service.
          See the <a href="https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/" target="_blank" rel="noopener noreferrer" className="text-splunk-green hover:underline">ACS API documentation</a> for more details.
        </p>
      </div>
    </div>
  );
}
