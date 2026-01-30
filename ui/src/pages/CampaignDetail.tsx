import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  BoltIcon,
  PlayIcon,
  PauseIcon,
  EyeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import type { AttackCampaign, AttackStep } from '../types';

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  const config: Record<string, { color: string; icon: React.ElementType; pulse?: boolean }> = {
    pending: { color: 'bg-yellow-100 text-yellow-700 border-yellow-300', icon: ClockIcon },
    running: { color: 'bg-red-100 text-red-700 border-red-300', icon: BoltIcon, pulse: true },
    paused: { color: 'bg-gray-100 text-gray-700 border-gray-300', icon: PauseIcon },
    completed: { color: 'bg-green-100 text-green-700 border-green-300', icon: CheckCircleIcon },
    detected: { color: 'bg-blue-100 text-blue-700 border-blue-300', icon: EyeIcon },
    failed: { color: 'bg-red-100 text-red-700 border-red-300', icon: ExclamationTriangleIcon },
  };

  const { color, icon: Icon, pulse } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full border ${color}`}>
      <Icon className={`h-4 w-4 mr-1.5 ${pulse ? 'animate-pulse' : ''}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function StepTimeline({ steps, currentPhase }: { steps: AttackStep[]; currentPhase: string }) {
  const phases = ['reconnaissance', 'initial_access', 'execution', 'persistence', 'privilege_escalation', 'defense_evasion', 'credential_access', 'discovery', 'lateral_movement', 'collection', 'command_and_control', 'exfiltration', 'impact'];

  const stepsByPhase = steps.reduce((acc, step) => {
    if (!acc[step.phase]) {
      acc[step.phase] = [];
    }
    acc[step.phase].push(step);
    return acc;
  }, {} as Record<string, AttackStep[]>);

  const activePhases = phases.filter((p) => stepsByPhase[p]?.length > 0);

  return (
    <div className="space-y-4">
      {activePhases.map((phase) => {
        const phaseSteps = stepsByPhase[phase] || [];
        const isActive = phase === currentPhase;
        const completedSteps = phaseSteps.filter((s) => s.success).length;
        const detectedSteps = phaseSteps.filter((s) => s.detected).length;

        return (
          <div key={phase} className={`border rounded-lg ${isActive ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}>
            <div className="p-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  {isActive && <BoltIcon className="h-4 w-4 text-red-500 mr-2 animate-pulse" />}
                  <h4 className="text-sm font-medium text-gray-900 capitalize">
                    {phase.replace(/_/g, ' ')}
                  </h4>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-green-600">{completedSteps} completed</span>
                  {detectedSteps > 0 && (
                    <span className="text-blue-600">{detectedSteps} detected</span>
                  )}
                </div>
              </div>
            </div>
            <div className="p-3 space-y-2">
              {phaseSteps.map((step) => (
                <div
                  key={step.id}
                  className={`flex items-center justify-between p-2 rounded ${
                    step.detected
                      ? 'bg-blue-50 border border-blue-200'
                      : step.success
                        ? 'bg-green-50 border border-green-200'
                        : 'bg-red-50 border border-red-200'
                  }`}
                >
                  <div className="flex items-center">
                    {step.detected ? (
                      <EyeIcon className="h-4 w-4 text-blue-500 mr-2" />
                    ) : step.success ? (
                      <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2" />
                    ) : (
                      <XCircleIcon className="h-4 w-4 text-red-500 mr-2" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900">{step.technique_name}</p>
                      <a
                        href={`https://attack.mitre.org/techniques/${step.technique_id.replace('.', '/')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-gray-500 hover:text-splunk-green"
                      >
                        {step.technique_id}
                      </a>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LogViewer({ campaignId }: { campaignId: string }) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['campaign-logs', campaignId],
    queryFn: () => attacksApi.getCampaignLogs(campaignId, 500),
    refetchInterval: 2000,
  });

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{logs.length} log entries</span>
        <label className="flex items-center text-sm text-gray-600">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="mr-2 h-4 w-4 text-splunk-green focus:ring-splunk-green border-gray-300 rounded"
          />
          Auto-scroll
        </label>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 h-96 overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-gray-500">No logs yet...</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="text-gray-300 mb-1 hover:bg-gray-800 px-1 rounded">
              <span className="text-gray-500">{new Date(log._time as string || Date.now()).toLocaleTimeString()}</span>
              {' '}
              <span className={`${log.severity === 'high' ? 'text-red-400' : log.severity === 'medium' ? 'text-yellow-400' : 'text-green-400'}`}>
                [{String(log.sourcetype || 'attack')}]
              </span>
              {' '}
              <span>{JSON.stringify(log, null, 0)}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'steps' | 'logs'>('steps');

  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => attacksApi.getCampaign(id!),
    enabled: !!id,
    refetchInterval: 3000,
  });

  const { data: steps = [] } = useQuery({
    queryKey: ['campaign-steps', id],
    queryFn: () => attacksApi.getCampaignSteps(id!),
    enabled: !!id,
    refetchInterval: 3000,
  });

  const startMutation = useMutation({
    mutationFn: () => attacksApi.startCampaign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => attacksApi.pauseCampaign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="space-y-4">
        <Link to="/attacks/campaigns" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to campaigns
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
            <span className="text-red-700">Campaign not found</span>
          </div>
        </div>
      </div>
    );
  }

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';
  const progressPercent = campaign.total_steps > 0
    ? Math.round((campaign.completed_steps / campaign.total_steps) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/attacks/campaigns" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to campaigns
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          <p className="mt-1 text-sm text-gray-500">Campaign ID: {campaign.id}</p>
        </div>
        <div className="flex items-center gap-3">
          {canStart && (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              {campaign.status === 'paused' ? 'Resume' : 'Start'} Campaign
            </button>
          )}
          {canPause && (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50"
            >
              <PauseIcon className="h-4 w-4 mr-2" />
              Pause Campaign
            </button>
          )}
        </div>
      </div>

      {/* Status Overview */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Status</h3>
            <div className="mt-2">
              <CampaignStatusBadge status={campaign.status} />
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-500">Threat Actor</h3>
            <p className="mt-2 text-lg font-semibold text-gray-900">{campaign.threat_actor_name}</p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-500">Current Phase</h3>
            <p className="mt-2 text-lg font-semibold text-gray-900 capitalize">
              {campaign.current_phase.replace(/_/g, ' ')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-500">Progress</h3>
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-red-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900">{progressPercent}%</span>
              </div>
              <p className="mt-1 text-sm text-gray-500">
                {campaign.completed_steps} of {campaign.total_steps} steps completed
              </p>
            </div>
          </div>
        </div>

        {/* Detection Alert */}
        {campaign.detected && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center">
              <EyeIcon className="h-5 w-5 text-blue-500 mr-2" />
              <div>
                <p className="text-sm font-medium text-blue-900">Attack Detected!</p>
                <p className="text-sm text-blue-700">
                  Detection occurred at step {campaign.detected_at_step} of {campaign.total_steps}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-gray-200">
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase">Target Instance</h4>
            <Link
              to={`/instances/${campaign.target_instance_id}`}
              className="mt-1 text-sm text-splunk-green hover:underline"
            >
              {campaign.target_instance_id}
            </Link>
          </div>
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase">Started</h4>
            <p className="mt-1 text-sm text-gray-900">
              {campaign.start_time ? new Date(campaign.start_time).toLocaleString() : 'Not started'}
            </p>
          </div>
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase">Ended</h4>
            <p className="mt-1 text-sm text-gray-900">
              {campaign.end_time ? new Date(campaign.end_time).toLocaleString() : '-'}
            </p>
          </div>
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase">Duration</h4>
            <p className="mt-1 text-sm text-gray-900">
              {campaign.start_time && campaign.end_time
                ? `${Math.round((new Date(campaign.end_time).getTime() - new Date(campaign.start_time).getTime()) / 60000)} minutes`
                : campaign.start_time
                  ? 'In progress...'
                  : '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('steps')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'steps'
                  ? 'border-splunk-green text-splunk-green'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <BoltIcon className="h-4 w-4 inline mr-2" />
              Attack Steps ({steps.length})
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'logs'
                  ? 'border-splunk-green text-splunk-green'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <DocumentTextIcon className="h-4 w-4 inline mr-2" />
              Generated Logs
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'steps' ? (
            steps.length === 0 ? (
              <div className="text-center py-8">
                <BoltIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No steps executed yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Start the campaign to begin the attack simulation.
                </p>
              </div>
            ) : (
              <StepTimeline steps={steps} currentPhase={campaign.current_phase} />
            )
          ) : (
            <LogViewer campaignId={campaign.id} />
          )}
        </div>
      </div>
    </div>
  );
}
