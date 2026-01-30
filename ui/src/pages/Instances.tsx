import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PlayIcon,
  StopIcon,
  TrashIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { instancesApi } from '../api';
import type { Instance } from '../types';

function StatusBadge({ status }: { status: Instance['status'] }) {
  const colors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    starting: 'bg-yellow-100 text-yellow-800 animate-pulse',
    stopped: 'bg-gray-100 text-gray-800',
    error: 'bg-red-100 text-red-800',
    pending: 'bg-blue-100 text-blue-800',
    provisioning: 'bg-blue-100 text-blue-800 animate-pulse',
    stopping: 'bg-yellow-100 text-yellow-800 animate-pulse',
    terminated: 'bg-gray-100 text-gray-500',
  };

  return (
    <span className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  );
}

function TopologyBadge({ topology }: { topology: string }) {
  const labels: Record<string, string> = {
    standalone: 'Standalone',
    distributed_minimal: 'Distributed',
    distributed_clustered: 'Clustered',
    victoria_full: 'Victoria Full',
  };

  return (
    <span className="inline-flex px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded">
      {labels[topology] || topology}
    </span>
  );
}

function InstanceRow({
  instance,
  onStart,
  onStop,
  onDestroy,
}: {
  instance: Instance;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onDestroy: (id: string) => void;
}) {
  const canStart = ['pending', 'stopped', 'provisioning'].includes(instance.status);
  const canStop = ['running', 'starting'].includes(instance.status);
  const canDestroy = !['terminated'].includes(instance.status);

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <Link to={`/instances/${instance.id}`} className="block">
          <div className="text-sm font-medium text-gray-900 hover:text-splunk-green">
            {instance.name}
          </div>
          <div className="text-xs text-gray-500 font-mono">{instance.id}</div>
        </Link>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <StatusBadge status={instance.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <TopologyBadge topology={instance.config.topology} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {instance.endpoints.web_url ? (
          <a
            href={instance.endpoints.web_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-splunk-green hover:underline"
          >
            Open Web UI
          </a>
        ) : (
          '-'
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <div title={format(new Date(instance.created_at), 'PPpp')}>
          {formatDistanceToNow(new Date(instance.created_at), { addSuffix: true })}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <div
          title={format(new Date(instance.expires_at), 'PPpp')}
          className={new Date(instance.expires_at) < new Date() ? 'text-red-500' : ''}
        >
          {formatDistanceToNow(new Date(instance.expires_at), { addSuffix: true })}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex justify-end gap-2">
          {canStart && (
            <button
              onClick={() => onStart(instance.id)}
              className="p-1 text-green-600 hover:text-green-800"
              title="Start"
            >
              <PlayIcon className="h-5 w-5" />
            </button>
          )}
          {canStop && (
            <button
              onClick={() => onStop(instance.id)}
              className="p-1 text-yellow-600 hover:text-yellow-800"
              title="Stop"
            >
              <StopIcon className="h-5 w-5" />
            </button>
          )}
          {canDestroy && (
            <button
              onClick={() => onDestroy(instance.id)}
              className="p-1 text-red-600 hover:text-red-800"
              title="Destroy"
            >
              <TrashIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function Instances() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('all');

  const { data: instances = [], isLoading, refetch } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: instancesApi.start,
    onSuccess: () => {
      toast.success('Instance starting...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to start: ${err.message}`),
  });

  const stopMutation = useMutation({
    mutationFn: instancesApi.stop,
    onSuccess: () => {
      toast.success('Instance stopping...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to stop: ${err.message}`),
  });

  const destroyMutation = useMutation({
    mutationFn: instancesApi.destroy,
    onSuccess: () => {
      toast.success('Instance destroyed');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
    onError: (err: Error) => toast.error(`Failed to destroy: ${err.message}`),
  });

  const handleDestroy = (id: string) => {
    if (window.confirm('Are you sure you want to destroy this instance? This cannot be undone.')) {
      destroyMutation.mutate(id);
    }
  };

  const filteredInstances = filter === 'all'
    ? instances
    : instances.filter((i) => i.status === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Instances</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your ephemeral Splunk Cloud Victoria instances
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <ArrowPathIcon className="h-4 w-4 mr-1" />
            Refresh
          </button>
          <Link
            to="/instances/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-splunk-green hover:bg-green-600"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            New Instance
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'running', 'stopped', 'pending', 'error'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1 text-sm rounded-full ${
              filter === status
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
            {status !== 'all' && (
              <span className="ml-1 text-xs">
                ({instances.filter((i) => i.status === status).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading instances...</div>
        ) : filteredInstances.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500 mb-4">
              {filter === 'all' ? 'No instances yet' : `No ${filter} instances`}
            </p>
            {filter === 'all' && (
              <Link
                to="/instances/new"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-splunk-green hover:bg-green-600"
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Create your first instance
              </Link>
            )}
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Topology
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  URL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Expires
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredInstances.map((instance) => (
                <InstanceRow
                  key={instance.id}
                  instance={instance}
                  onStart={(id) => startMutation.mutate(id)}
                  onStop={(id) => stopMutation.mutate(id)}
                  onDestroy={handleDestroy}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
