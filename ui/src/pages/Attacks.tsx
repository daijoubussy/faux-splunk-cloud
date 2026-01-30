import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  UserGroupIcon,
  BoltIcon,
  PlayCircleIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';

function StatCard({
  title,
  value,
  icon: Icon,
  href,
  description,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  href: string;
  description: string;
}) {
  return (
    <Link
      to={href}
      className="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
    >
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0 bg-red-100 rounded-md p-3">
            <Icon className="h-6 w-6 text-red-600" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="text-2xl font-semibold text-gray-900">{value}</dd>
            </dl>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-500">{description}</p>
      </div>
    </Link>
  );
}

export default function Attacks() {
  const { data: threatActors = [] } = useQuery({
    queryKey: ['threat-actors'],
    queryFn: attacksApi.listThreatActors,
  });

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
  });

  const { data: scenarios = [] } = useQuery({
    queryKey: ['scenarios'],
    queryFn: attacksApi.listScenarios,
  });

  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Attack Simulation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Simulate adversarial attacks for security training and detection testing
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Threat Actors"
          value={threatActors.length}
          icon={UserGroupIcon}
          href="/attacks/threat-actors"
          description="From script kiddies to nation-state APTs"
        />
        <StatCard
          title="Active Campaigns"
          value={activeCampaigns}
          icon={BoltIcon}
          href="/attacks/campaigns"
          description="Currently running attack simulations"
        />
        <StatCard
          title="Total Campaigns"
          value={campaigns.length}
          icon={PlayCircleIcon}
          href="/attacks/campaigns"
          description="All attack campaigns"
        />
        <StatCard
          title="Scenarios"
          value={scenarios.length}
          icon={ShieldExclamationIcon}
          href="/attacks/scenarios"
          description="Pre-built attack scenarios"
        />
      </div>

      {/* Quick Links */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Links</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to="/attacks/threat-actors"
            className="flex items-center p-4 border rounded-lg hover:border-splunk-green hover:bg-green-50 transition-colors"
          >
            <UserGroupIcon className="h-8 w-8 text-red-500 mr-3" />
            <div>
              <h3 className="font-medium text-gray-900">Threat Actors</h3>
              <p className="text-sm text-gray-500">Browse adversary profiles</p>
            </div>
          </Link>
          <Link
            to="/attacks/campaigns"
            className="flex items-center p-4 border rounded-lg hover:border-splunk-green hover:bg-green-50 transition-colors"
          >
            <BoltIcon className="h-8 w-8 text-yellow-500 mr-3" />
            <div>
              <h3 className="font-medium text-gray-900">Campaigns</h3>
              <p className="text-sm text-gray-500">View active attacks</p>
            </div>
          </Link>
          <Link
            to="/attacks/scenarios"
            className="flex items-center p-4 border rounded-lg hover:border-splunk-green hover:bg-green-50 transition-colors"
          >
            <ShieldExclamationIcon className="h-8 w-8 text-purple-500 mr-3" />
            <div>
              <h3 className="font-medium text-gray-900">Scenarios</h3>
              <p className="text-sm text-gray-500">Run pre-built attacks</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Featured Threat Actors */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Featured Threat Actors</h3>
            <Link to="/attacks/threat-actors" className="text-sm text-splunk-green hover:underline">
              View all
            </Link>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {threatActors.slice(0, 5).map((actor) => (
            <div key={actor.id} className="px-4 py-4 sm:px-6 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900">{actor.name}</h4>
                  <p className="text-xs text-gray-500">
                    {actor.aliases.slice(0, 3).join(', ')}
                    {actor.aliases.length > 3 && ` +${actor.aliases.length - 3} more`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <ThreatLevelBadge level={actor.threat_level} />
                  {actor.attributed_country && (
                    <span className="text-xs text-gray-500">{actor.attributed_country}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ThreatLevelBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    script_kiddie: 'bg-gray-100 text-gray-700',
    opportunistic: 'bg-yellow-100 text-yellow-700',
    organized_crime: 'bg-orange-100 text-orange-700',
    hacktivist: 'bg-purple-100 text-purple-700',
    insider_threat: 'bg-pink-100 text-pink-700',
    apt: 'bg-red-100 text-red-700',
    nation_state: 'bg-red-200 text-red-900',
  };

  const labels: Record<string, string> = {
    script_kiddie: 'Script Kiddie',
    opportunistic: 'Opportunistic',
    organized_crime: 'Organized Crime',
    hacktivist: 'Hacktivist',
    insider_threat: 'Insider',
    apt: 'APT',
    nation_state: 'Nation State',
  };

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${colors[level] || 'bg-gray-100'}`}>
      {labels[level] || level}
    </span>
  );
}
