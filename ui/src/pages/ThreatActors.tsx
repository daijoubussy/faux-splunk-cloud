import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  UserGroupIcon,
  MagnifyingGlassIcon,
  GlobeAltIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import type { ThreatActor } from '../types';

const threatLevelOrder: Record<string, number> = {
  nation_state: 7,
  apt: 6,
  insider_threat: 5,
  organized_crime: 4,
  hacktivist: 3,
  opportunistic: 2,
  script_kiddie: 1,
};

function ThreatLevelBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    script_kiddie: 'bg-gray-100 text-gray-700 border-gray-300',
    opportunistic: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    organized_crime: 'bg-orange-100 text-orange-700 border-orange-300',
    hacktivist: 'bg-purple-100 text-purple-700 border-purple-300',
    insider_threat: 'bg-pink-100 text-pink-700 border-pink-300',
    apt: 'bg-red-100 text-red-700 border-red-300',
    nation_state: 'bg-red-200 text-red-900 border-red-400',
  };

  const labels: Record<string, string> = {
    script_kiddie: 'Script Kiddie',
    opportunistic: 'Opportunistic',
    organized_crime: 'Organized Crime',
    hacktivist: 'Hacktivist',
    insider_threat: 'Insider Threat',
    apt: 'APT',
    nation_state: 'Nation State',
  };

  return (
    <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full border ${colors[level] || 'bg-gray-100'}`}>
      {labels[level] || level}
    </span>
  );
}

function MotivationBadge({ motivation }: { motivation: string }) {
  const colors: Record<string, string> = {
    financial: 'bg-green-50 text-green-700',
    espionage: 'bg-blue-50 text-blue-700',
    disruption: 'bg-red-50 text-red-700',
    ideology: 'bg-purple-50 text-purple-700',
    notoriety: 'bg-yellow-50 text-yellow-700',
    revenge: 'bg-orange-50 text-orange-700',
  };

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs rounded ${colors[motivation] || 'bg-gray-50 text-gray-700'}`}>
      {motivation}
    </span>
  );
}

function ThreatActorCard({ actor }: { actor: ThreatActor }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-red-100 rounded-full p-3">
              <UserGroupIcon className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">{actor.name}</h3>
              <p className="text-sm text-gray-500">
                {actor.aliases.slice(0, 3).join(', ')}
                {actor.aliases.length > 3 && ` +${actor.aliases.length - 3} more`}
              </p>
            </div>
          </div>
          <ThreatLevelBadge level={actor.threat_level} />
        </div>

        <p className="mt-4 text-sm text-gray-600 line-clamp-2">{actor.description}</p>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {actor.motivation.map((mot) => (
            <MotivationBadge key={mot} motivation={mot} />
          ))}
        </div>

        {actor.attributed_country && (
          <div className="mt-3 flex items-center text-sm text-gray-500">
            <GlobeAltIcon className="h-4 w-4 mr-1" />
            <span>Attributed: {actor.attributed_country}</span>
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 text-sm text-splunk-green hover:underline"
        >
          {expanded ? 'Show less' : `View ${actor.techniques.length} techniques`}
        </button>

        {expanded && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg">
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">MITRE ATT&CK Techniques</h4>
            <div className="flex flex-wrap gap-1.5">
              {actor.techniques.map((tech) => (
                <a
                  key={tech}
                  href={`https://attack.mitre.org/techniques/${tech.replace('.', '/')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex px-2 py-0.5 text-xs bg-white border rounded hover:bg-gray-100"
                >
                  {tech}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100">
        <Link
          to={`/attacks/campaigns?threat_actor=${actor.id}`}
          className="text-sm text-splunk-green hover:underline"
        >
          View campaigns using this actor
        </Link>
      </div>
    </div>
  );
}

export default function ThreatActors() {
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');

  const { data: threatActors = [], isLoading, error } = useQuery({
    queryKey: ['threat-actors'],
    queryFn: attacksApi.listThreatActors,
  });

  const filteredActors = threatActors
    .filter((actor) => {
      if (levelFilter !== 'all' && actor.threat_level !== levelFilter) {
        return false;
      }
      if (search) {
        const searchLower = search.toLowerCase();
        return (
          actor.name.toLowerCase().includes(searchLower) ||
          actor.aliases.some((a) => a.toLowerCase().includes(searchLower)) ||
          actor.description.toLowerCase().includes(searchLower)
        );
      }
      return true;
    })
    .sort((a, b) => {
      return (threatLevelOrder[b.threat_level] || 0) - (threatLevelOrder[a.threat_level] || 0);
    });

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
          <span className="text-red-700">Failed to load threat actors</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Threat Actors</h1>
        <p className="mt-1 text-sm text-gray-500">
          Browse adversary profiles from script kiddies to nation-state APTs
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="search" className="sr-only">Search threat actors</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="search"
                type="text"
                placeholder="Search by name, alias, or description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
              />
            </div>
          </div>

          <div className="sm:w-48">
            <label htmlFor="level-filter" className="sr-only">Filter by threat level</label>
            <select
              id="level-filter"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-splunk-green focus:border-splunk-green sm:text-sm"
            >
              <option value="all">All Threat Levels</option>
              <option value="nation_state">Nation State</option>
              <option value="apt">APT</option>
              <option value="insider_threat">Insider Threat</option>
              <option value="organized_crime">Organized Crime</option>
              <option value="hacktivist">Hacktivist</option>
              <option value="opportunistic">Opportunistic</option>
              <option value="script_kiddie">Script Kiddie</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results count */}
      <div className="text-sm text-gray-500">
        Showing {filteredActors.length} of {threatActors.length} threat actors
      </div>

      {/* Grid of cards */}
      {filteredActors.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No threat actors found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your search or filter criteria.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredActors.map((actor) => (
            <ThreatActorCard key={actor.id} actor={actor} />
          ))}
        </div>
      )}
    </div>
  );
}
