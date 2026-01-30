import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BoltIcon,
  PlayIcon,
  PauseIcon,
  EyeIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import type { AttackCampaign } from '../types';

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  const config: Record<string, { color: string; icon: React.ElementType; pulse?: boolean }> = {
    pending: { color: 'bg-yellow-100 text-yellow-700', icon: ClockIcon },
    running: { color: 'bg-red-100 text-red-700', icon: BoltIcon, pulse: true },
    paused: { color: 'bg-gray-100 text-gray-700', icon: PauseIcon },
    completed: { color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
    detected: { color: 'bg-blue-100 text-blue-700', icon: EyeIcon },
    failed: { color: 'bg-red-100 text-red-700', icon: ExclamationTriangleIcon },
  };

  const { color, icon: Icon, pulse } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-full ${color}`}>
      <Icon className={`h-3.5 w-3.5 mr-1 ${pulse ? 'animate-pulse' : ''}`} />
      {status}
    </span>
  );
}

function ProgressBar({ completed, total }: { completed: number; total: number }) {
  const percentage = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-red-500 h-full rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 whitespace-nowrap">
        {completed}/{total}
      </span>
    </div>
  );
}

function CampaignRow({ campaign }: { campaign: AttackCampaign }) {
  const queryClient = useQueryClient();

  const startMutation = useMutation({
    mutationFn: () => attacksApi.startCampaign(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => attacksApi.pauseCampaign(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="flex-shrink-0 bg-red-100 rounded-full p-2">
            <BoltIcon className="h-5 w-5 text-red-600" />
          </div>
          <div className="ml-4">
            <Link
              to={`/attacks/campaigns/${campaign.id}`}
              className="text-sm font-medium text-gray-900 hover:text-splunk-green"
            >
              {campaign.name}
            </Link>
            <p className="text-xs text-gray-500">{campaign.id}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">{campaign.threat_actor_name}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-500">{campaign.current_phase}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="w-32">
          <ProgressBar completed={campaign.completed_steps} total={campaign.total_steps} />
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <CampaignStatusBadge status={campaign.status} />
        {campaign.detected && (
          <span className="ml-2 inline-flex items-center px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded">
            <EyeIcon className="h-3 w-3 mr-1" />
            Detected
          </span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {campaign.start_time
          ? new Date(campaign.start_time).toLocaleString()
          : 'Not started'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex items-center justify-end gap-2">
          {canStart && (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="p-1.5 text-green-600 hover:bg-green-50 rounded-md disabled:opacity-50"
              title="Start campaign"
            >
              <PlayIcon className="h-4 w-4" />
            </button>
          )}
          {canPause && (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded-md disabled:opacity-50"
              title="Pause campaign"
            >
              <PauseIcon className="h-4 w-4" />
            </button>
          )}
          <Link
            to={`/attacks/campaigns/${campaign.id}`}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md"
            title="View details"
          >
            <EyeIcon className="h-4 w-4" />
          </Link>
        </div>
      </td>
    </tr>
  );
}

export default function Campaigns() {
  const [searchParams] = useSearchParams();
  const threatActorFilter = searchParams.get('threat_actor') || '';
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data: campaigns = [], isLoading, error } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
    refetchInterval: 5000, // Refresh every 5 seconds for active campaigns
  });

  const filteredCampaigns = campaigns.filter((campaign) => {
    if (statusFilter !== 'all' && campaign.status !== statusFilter) {
      return false;
    }
    if (threatActorFilter && campaign.threat_actor_id !== threatActorFilter) {
      return false;
    }
    return true;
  });

  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;
  const completedCampaigns = campaigns.filter((c) => c.status === 'completed').length;
  const detectedCampaigns = campaigns.filter((c) => c.detected).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-splunk-green"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">Failed to load campaigns</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Attack Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and monitor active attack simulations
          </p>
        </div>
        <Link
          to="/attacks/scenarios"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700"
        >
          <BoltIcon className="h-4 w-4 mr-2" />
          Launch New Attack
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-gray-100 rounded-md p-3">
                <BoltIcon className="h-6 w-6 text-gray-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Campaigns</dt>
                  <dd className="text-2xl font-semibold text-gray-900">{campaigns.length}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-red-100 rounded-md p-3">
                <PlayIcon className="h-6 w-6 text-red-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Active</dt>
                  <dd className="text-2xl font-semibold text-gray-900">{activeCampaigns}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-green-100 rounded-md p-3">
                <CheckCircleIcon className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Completed</dt>
                  <dd className="text-2xl font-semibold text-gray-900">{completedCampaigns}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-blue-100 rounded-md p-3">
                <EyeIcon className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Detected</dt>
                  <dd className="text-2xl font-semibold text-gray-900">{detectedCampaigns}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <div className="sm:w-48">
            <label htmlFor="status-filter" className="sr-only">Filter by status</label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
            >
              <option value="all">All Statuses</option>
              <option value="running">Running</option>
              <option value="pending">Pending</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="detected">Detected</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {threatActorFilter && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>Filtered by threat actor:</span>
              <span className="font-medium">{threatActorFilter}</span>
              <Link
                to="/attacks/campaigns"
                className="text-splunk-green hover:underline"
              >
                Clear
              </Link>
            </div>
          )}

          <div className="flex-1 text-right text-sm text-gray-500">
            Showing {filteredCampaigns.length} of {campaigns.length} campaigns
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {filteredCampaigns.length === 0 ? (
          <div className="p-8 text-center">
            <BoltIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No campaigns found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {campaigns.length === 0
                ? 'Launch a new attack from the Scenarios page.'
                : 'Try adjusting your filter criteria.'}
            </p>
            <div className="mt-6">
              <Link
                to="/attacks/scenarios"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700"
              >
                <BoltIcon className="h-4 w-4 mr-2" />
                Launch Attack
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Campaign
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Threat Actor
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Phase
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Started
                  </th>
                  <th scope="col" className="relative px-6 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredCampaigns.map((campaign) => (
                  <CampaignRow key={campaign.id} campaign={campaign} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
