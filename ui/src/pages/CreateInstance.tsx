import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { instancesApi } from '../api';
import type { InstanceCreate } from '../types';

const topologies = [
  {
    id: 'standalone',
    name: 'Standalone',
    description: 'Single Splunk instance. Quick startup, minimal resources.',
    resources: '~2GB RAM',
  },
  {
    id: 'distributed_minimal',
    name: 'Distributed Minimal',
    description: 'Separate Search Head and Indexer. Better for testing distributed features.',
    resources: '~4GB RAM',
  },
  {
    id: 'distributed_clustered',
    name: 'Distributed Clustered',
    description: 'Search Head Cluster + Indexer Cluster. Production-like setup.',
    resources: '~8GB RAM',
  },
  {
    id: 'victoria_full',
    name: 'Victoria Full',
    description: 'Full Victoria Experience with all components. Most realistic.',
    resources: '~12GB RAM',
  },
];

export default function CreateInstance() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    name: '',
    topology: 'standalone',
    ttl_hours: 24,
    enable_hec: true,
    enable_realtime_search: true,
    create_default_indexes: true,
    memory_mb: 2048,
    cpu_cores: 1.0,
  });

  const createMutation = useMutation({
    mutationFn: (data: InstanceCreate) => instancesApi.create(data),
    onSuccess: (instance) => {
      toast.success('Instance created! Starting...');
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate(`/instances/${instance.id}`);
    },
    onError: (err: Error) => {
      toast.error(`Failed to create instance: ${err.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.match(/^[a-z][a-z0-9-]*[a-z0-9]$/)) {
      toast.error('Name must be lowercase, alphanumeric, and can contain hyphens');
      return;
    }

    createMutation.mutate({
      name: formData.name,
      config: {
        topology: formData.topology as InstanceCreate['config']['topology'],
        enable_hec: formData.enable_hec,
        enable_realtime_search: formData.enable_realtime_search,
        create_default_indexes: formData.create_default_indexes,
        memory_mb: formData.memory_mb,
        cpu_cores: formData.cpu_cores,
      },
      ttl_hours: formData.ttl_hours,
    });
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Create New Instance</h1>
        <p className="mt-1 text-sm text-gray-500">
          Provision an ephemeral Splunk Cloud Victoria instance
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h2>

          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Instance Name
            </label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value.toLowerCase() })}
              placeholder="my-test-splunk"
              pattern="^[a-z][a-z0-9-]*[a-z0-9]$"
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-splunk-green focus:ring-splunk-green sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Lowercase letters, numbers, and hyphens only
            </p>
          </div>

          <div className="mt-4">
            <label htmlFor="ttl" className="block text-sm font-medium text-gray-700">
              Time to Live (hours)
            </label>
            <input
              type="number"
              id="ttl"
              value={formData.ttl_hours}
              onChange={(e) => setFormData({ ...formData, ttl_hours: parseInt(e.target.value) })}
              min={1}
              max={168}
              className="mt-1 block w-32 rounded-md border-gray-300 shadow-sm focus:border-splunk-green focus:ring-splunk-green sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Instance will be automatically destroyed after this time (max 168 hours / 1 week)
            </p>
          </div>
        </div>

        {/* Topology */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Topology</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {topologies.map((topology) => (
              <label
                key={topology.id}
                className={`relative flex cursor-pointer rounded-lg border p-4 shadow-sm focus:outline-none ${
                  formData.topology === topology.id
                    ? 'border-splunk-green ring-2 ring-splunk-green'
                    : 'border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="topology"
                  value={topology.id}
                  checked={formData.topology === topology.id}
                  onChange={(e) => setFormData({ ...formData, topology: e.target.value })}
                  className="sr-only"
                />
                <div className="flex flex-1 flex-col">
                  <span className="block text-sm font-medium text-gray-900">{topology.name}</span>
                  <span className="mt-1 text-xs text-gray-500">{topology.description}</span>
                  <span className="mt-2 text-xs font-medium text-gray-700">{topology.resources}</span>
                </div>
                {formData.topology === topology.id && (
                  <div className="absolute -inset-px rounded-lg border-2 border-splunk-green pointer-events-none" />
                )}
              </label>
            ))}
          </div>
        </div>

        {/* Victoria Options */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Victoria Experience Options</h2>

          <div className="space-y-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.enable_hec}
                onChange={(e) => setFormData({ ...formData, enable_hec: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-splunk-green focus:ring-splunk-green"
              />
              <span className="ml-2 text-sm text-gray-700">Enable HTTP Event Collector (HEC)</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.enable_realtime_search}
                onChange={(e) => setFormData({ ...formData, enable_realtime_search: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-splunk-green focus:ring-splunk-green"
              />
              <span className="ml-2 text-sm text-gray-700">Enable Real-time Search</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.create_default_indexes}
                onChange={(e) => setFormData({ ...formData, create_default_indexes: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-splunk-green focus:ring-splunk-green"
              />
              <span className="ml-2 text-sm text-gray-700">Create Default Indexes (main, summary, etc.)</span>
            </label>
          </div>
        </div>

        {/* Resources */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Resources</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="memory" className="block text-sm font-medium text-gray-700">
                Memory (MB)
              </label>
              <select
                id="memory"
                value={formData.memory_mb}
                onChange={(e) => setFormData({ ...formData, memory_mb: parseInt(e.target.value) })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-splunk-green focus:ring-splunk-green sm:text-sm"
              >
                <option value={512}>512 MB</option>
                <option value={1024}>1 GB</option>
                <option value={2048}>2 GB</option>
                <option value={4096}>4 GB</option>
                <option value={8192}>8 GB</option>
              </select>
            </div>

            <div>
              <label htmlFor="cpu" className="block text-sm font-medium text-gray-700">
                CPU Cores
              </label>
              <select
                id="cpu"
                value={formData.cpu_cores}
                onChange={(e) => setFormData({ ...formData, cpu_cores: parseFloat(e.target.value) })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-splunk-green focus:ring-splunk-green sm:text-sm"
              >
                <option value={0.5}>0.5 cores</option>
                <option value={1.0}>1.0 cores</option>
                <option value={2.0}>2.0 cores</option>
                <option value={4.0}>4.0 cores</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/instances')}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-splunk-green hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Instance'}
          </button>
        </div>
      </form>
    </div>
  );
}
