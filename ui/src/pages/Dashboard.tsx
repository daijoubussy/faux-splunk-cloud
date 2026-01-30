import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ServerIcon,
  ShieldExclamationIcon,
  PlayIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { instancesApi, attacksApi } from '../api';
import type { Instance, AttackCampaign } from '../types';

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  href,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
    >
      <div className="p-5">
        <div className="flex items-center">
          <div className={`flex-shrink-0 ${color} rounded-md p-3`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="text-2xl font-semibold text-gray-900">{value}</dd>
            </dl>
          </div>
        </div>
      </div>
    </Link>
  );
}

function InstanceList({ instances }: { instances: Instance[] }) {
  const recentInstances = instances.slice(0, 5);

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Recent Instances</h3>
          <Link to="/instances" className="text-sm text-splunk-green hover:underline">
            View all
          </Link>
        </div>
      </div>
      <ul className="divide-y divide-gray-200">
        {recentInstances.length === 0 ? (
          <li className="px-4 py-4 text-gray-500 text-center">No instances yet</li>
        ) : (
          recentInstances.map((instance) => (
            <li key={instance.id}>
              <Link
                to={`/instances/${instance.id}`}
                className="block hover:bg-gray-50 px-4 py-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <ServerIcon className="h-5 w-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{instance.name}</p>
                      <p className="text-xs text-gray-500">{instance.id}</p>
                    </div>
                  </div>
                  <StatusBadge status={instance.status} />
                </div>
              </Link>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function CampaignList({ campaigns }: { campaigns: AttackCampaign[] }) {
  const recentCampaigns = campaigns.slice(0, 5);

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Active Campaigns</h3>
          <Link to="/attacks/campaigns" className="text-sm text-splunk-green hover:underline">
            View all
          </Link>
        </div>
      </div>
      <ul className="divide-y divide-gray-200">
        {recentCampaigns.length === 0 ? (
          <li className="px-4 py-4 text-gray-500 text-center">No campaigns running</li>
        ) : (
          recentCampaigns.map((campaign) => (
            <li key={campaign.id}>
              <Link
                to={`/attacks/campaigns/${campaign.id}`}
                className="block hover:bg-gray-50 px-4 py-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <ShieldExclamationIcon className="h-5 w-5 text-red-500 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{campaign.name}</p>
                      <p className="text-xs text-gray-500">{campaign.threat_actor_name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {campaign.completed_steps}/{campaign.total_steps} steps
                    </span>
                    <CampaignStatusBadge status={campaign.status} />
                  </div>
                </div>
              </Link>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function StatusBadge({ status }: { status: Instance['status'] }) {
  const colors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    starting: 'bg-yellow-100 text-yellow-800',
    stopped: 'bg-gray-100 text-gray-800',
    error: 'bg-red-100 text-red-800',
    pending: 'bg-blue-100 text-blue-800',
    provisioning: 'bg-blue-100 text-blue-800',
  };

  return (
    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  );
}

function CampaignStatusBadge({ status }: { status: AttackCampaign['status'] }) {
  const colors: Record<string, string> = {
    running: 'bg-red-100 text-red-800',
    pending: 'bg-yellow-100 text-yellow-800',
    paused: 'bg-gray-100 text-gray-800',
    completed: 'bg-green-100 text-green-800',
    detected: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  );
}

export default function Dashboard() {
  const { data: instances = [], isLoading: loadingInstances } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
  });

  const { data: campaigns = [], isLoading: loadingCampaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
  });

  const runningInstances = instances.filter((i) => i.status === 'running').length;
  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;
  const errorInstances = instances.filter((i) => i.status === 'error').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your ephemeral Splunk Cloud instances and attack simulations
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Instances"
          value={loadingInstances ? '...' : instances.length}
          icon={ServerIcon}
          color="bg-blue-500"
          href="/instances"
        />
        <StatCard
          title="Running"
          value={loadingInstances ? '...' : runningInstances}
          icon={PlayIcon}
          color="bg-green-500"
          href="/instances?status=running"
        />
        <StatCard
          title="Active Attacks"
          value={loadingCampaigns ? '...' : activeCampaigns}
          icon={ShieldExclamationIcon}
          color="bg-red-500"
          href="/attacks/campaigns"
        />
        <StatCard
          title="Errors"
          value={loadingInstances ? '...' : errorInstances}
          icon={ExclamationTriangleIcon}
          color="bg-yellow-500"
          href="/instances?status=error"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/instances/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-splunk-green hover:bg-green-600"
          >
            <ServerIcon className="h-4 w-4 mr-2" />
            New Instance
          </Link>
          <Link
            to="/attacks/scenarios"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700"
          >
            <ShieldExclamationIcon className="h-4 w-4 mr-2" />
            Run Attack Scenario
          </Link>
          <Link
            to="/attacks/threat-actors"
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Browse Threat Actors
          </Link>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <InstanceList instances={instances} />
        <CampaignList campaigns={campaigns} />
      </div>
    </div>
  );
}
