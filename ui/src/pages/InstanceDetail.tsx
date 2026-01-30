import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import {
  PlayIcon,
  StopIcon,
  TrashIcon,
  ClockIcon,
  ArrowTopRightOnSquareIcon,
  ClipboardIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { instancesApi, attacksApi } from '../api';
import type { Instance } from '../types';

function StatusBadge({ status }: { status: Instance['status'] }) {
  const colors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    starting: 'bg-yellow-100 text-yellow-800 animate-pulse',
    stopped: 'bg-gray-100 text-gray-800',
    error: 'bg-red-100 text-red-800',
    pending: 'bg-blue-100 text-blue-800',
    provisioning: 'bg-blue-100 text-blue-800 animate-pulse',
  };

  return (
    <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    toast.success(`${label} copied to clipboard`);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 text-gray-400 hover:text-gray-600"
      title={`Copy ${label}`}
    >
      <ClipboardIcon className="h-4 w-4" />
    </button>
  );
}

function InfoRow({ label, value, copyable = false }: { label: string; value: string | null; copyable?: boolean }) {
  if (!value) return null;

  return (
    <div className="py-3 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 flex items-center gap-2 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
        <span className="font-mono break-all">{value}</span>
        {copyable && <CopyButton value={value} label={label} />}
      </dd>
    </div>
  );
}

function LogViewer({ instanceId }: { instanceId: string }) {
  const [tail, setTail] = useState(100);

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['instance-logs', instanceId, tail],
    queryFn: () => instancesApi.getLogs(instanceId, tail),
    refetchInterval: 5000,
  });

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:px-6 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Container Logs</h3>
        <div className="flex items-center gap-2">
          <select
            value={tail}
            onChange={(e) => setTail(parseInt(e.target.value))}
            className="text-sm border-gray-300 rounded-md"
          >
            <option value={50}>Last 50 lines</option>
            <option value={100}>Last 100 lines</option>
            <option value={500}>Last 500 lines</option>
          </select>
          <button
            onClick={() => refetch()}
            className="px-2 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      </div>
      <div className="p-4">
        {isLoading ? (
          <div className="text-gray-500">Loading logs...</div>
        ) : (
          <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto max-h-96">
            {logs || 'No logs available'}
          </pre>
        )}
      </div>
    </div>
  );
}

export default function InstanceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showLogs, setShowLogs] = useState(false);

  const { data: instance, isLoading, error } = useQuery({
    queryKey: ['instance', id],
    queryFn: () => instancesApi.get(id!),
    enabled: !!id,
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: () => instancesApi.start(id!),
    onSuccess: () => {
      toast.success('Instance starting...');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const stopMutation = useMutation({
    mutationFn: () => instancesApi.stop(id!),
    onSuccess: () => {
      toast.success('Instance stopping...');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const destroyMutation = useMutation({
    mutationFn: () => instancesApi.destroy(id!),
    onSuccess: () => {
      toast.success('Instance destroyed');
      navigate('/instances');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const extendMutation = useMutation({
    mutationFn: (hours: number) => instancesApi.extend(id!, hours),
    onSuccess: () => {
      toast.success('TTL extended');
      queryClient.invalidateQueries({ queryKey: ['instance', id] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const launchAttackMutation = useMutation({
    mutationFn: (threatActorId: string) =>
      attacksApi.createCampaign({
        threat_actor_id: threatActorId,
        target_instance_id: id!,
        start_immediately: true,
      }),
    onSuccess: (campaign) => {
      toast.success('Attack campaign started!');
      navigate(`/attacks/campaigns/${campaign.id}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (error || !instance) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">Failed to load instance</p>
        <Link to="/instances" className="text-splunk-green hover:underline mt-2 inline-block">
          Back to instances
        </Link>
      </div>
    );
  }

  const canStart = ['pending', 'stopped', 'provisioning'].includes(instance.status);
  const canStop = ['running', 'starting'].includes(instance.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{instance.name}</h1>
            <StatusBadge status={instance.status} />
          </div>
          <p className="mt-1 text-sm text-gray-500 font-mono">{instance.id}</p>
        </div>
        <div className="flex gap-2">
          {canStart && (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              <PlayIcon className="h-4 w-4 mr-1" />
              Start
            </button>
          )}
          {canStop && (
            <button
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50"
            >
              <StopIcon className="h-4 w-4 mr-1" />
              Stop
            </button>
          )}
          <button
            onClick={() => {
              if (window.confirm('Destroy this instance?')) destroyMutation.mutate();
            }}
            disabled={destroyMutation.isPending}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
          >
            <TrashIcon className="h-4 w-4 mr-1" />
            Destroy
          </button>
        </div>
      </div>

      {/* Quick Access */}
      {instance.status === 'running' && instance.endpoints.web_url && (
        <div className="bg-splunk-green/10 border border-splunk-green rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Splunk is Ready!</h3>
              <p className="text-sm text-gray-600">Access your Splunk instance</p>
            </div>
            <a
              href={instance.endpoints.web_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-splunk-green hover:bg-green-600"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
              Open Splunk Web
            </a>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Instance Info */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Instance Information</h3>
          </div>
          <div className="px-4 py-5 sm:px-6">
            <dl className="divide-y divide-gray-200">
              <InfoRow label="Topology" value={instance.config.topology} />
              <InfoRow label="Experience" value={instance.config.experience} />
              <InfoRow label="Memory" value={`${instance.config.memory_mb} MB`} />
              <InfoRow label="CPU" value={`${instance.config.cpu_cores} cores`} />
              <InfoRow
                label="Created"
                value={format(new Date(instance.created_at), 'PPpp')}
              />
              <div className="py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-gray-500">Expires</dt>
                <dd className="mt-1 flex items-center gap-2 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
                  <span>{formatDistanceToNow(new Date(instance.expires_at), { addSuffix: true })}</span>
                  <button
                    onClick={() => extendMutation.mutate(24)}
                    className="inline-flex items-center px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
                  >
                    <ClockIcon className="h-3 w-3 mr-1" />
                    +24h
                  </button>
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Endpoints */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Endpoints</h3>
          </div>
          <div className="px-4 py-5 sm:px-6">
            <dl className="divide-y divide-gray-200">
              <InfoRow label="Web UI" value={instance.endpoints.web_url} copyable />
              <InfoRow label="REST API" value={instance.endpoints.api_url} copyable />
              <InfoRow label="HEC" value={instance.endpoints.hec_url} copyable />
              <InfoRow label="ACS API" value={instance.endpoints.acs_url} copyable />
            </dl>
          </div>
        </div>

        {/* Credentials */}
        {instance.credentials && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Credentials</h3>
            </div>
            <div className="px-4 py-5 sm:px-6">
              <dl className="divide-y divide-gray-200">
                <InfoRow label="Username" value={instance.credentials.admin_username} copyable />
                <InfoRow label="Password" value={instance.credentials.admin_password} copyable />
                <InfoRow label="HEC Token" value={instance.credentials.hec_token} copyable />
                <InfoRow label="ACS Token" value={instance.credentials.acs_token} copyable />
              </dl>
            </div>
          </div>
        )}

        {/* Attack Simulation */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Attack Simulation</h3>
          </div>
          <div className="px-4 py-5 sm:px-6">
            <p className="text-sm text-gray-600 mb-4">
              Launch a simulated attack against this instance
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'script_kiddie_generic', label: 'Script Kiddie', color: 'bg-gray-500' },
                { id: 'apt_generic', label: 'Generic APT', color: 'bg-orange-500' },
                { id: 'apt29', label: 'APT29 (Cozy Bear)', color: 'bg-red-600' },
                { id: 'lazarus', label: 'Lazarus Group', color: 'bg-red-700' },
              ].map((actor) => (
                <button
                  key={actor.id}
                  onClick={() => launchAttackMutation.mutate(actor.id)}
                  disabled={instance.status !== 'running' || launchAttackMutation.isPending}
                  className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md text-white ${actor.color} hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <ShieldExclamationIcon className="h-3 w-3 mr-1" />
                  {actor.label}
                </button>
              ))}
            </div>
            <Link
              to="/attacks/scenarios"
              className="inline-block mt-3 text-sm text-splunk-green hover:underline"
            >
              View all attack scenarios →
            </Link>
          </div>
        </div>
      </div>

      {/* Logs Toggle */}
      <div>
        <button
          onClick={() => setShowLogs(!showLogs)}
          className="text-sm text-splunk-green hover:underline"
        >
          {showLogs ? 'Hide Logs' : 'Show Container Logs'}
        </button>
      </div>

      {showLogs && id && <LogViewer instanceId={id} />}
    </div>
  );
}
