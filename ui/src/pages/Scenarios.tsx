import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ShieldExclamationIcon,
  BoltIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ServerIcon,
} from '@heroicons/react/24/outline';
import { attacksApi, instancesApi } from '../api';
import type { AttackScenario, Instance } from '../types';

function ThreatLevelIndicator({ level }: { level: string }) {
  const levels: Record<string, { color: string; bars: number }> = {
    low: { color: 'bg-green-500', bars: 1 },
    medium: { color: 'bg-yellow-500', bars: 2 },
    high: { color: 'bg-orange-500', bars: 3 },
    critical: { color: 'bg-red-500', bars: 4 },
  };

  const config = levels[level] || levels.medium;

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4].map((bar) => (
        <div
          key={bar}
          className={`w-1.5 h-${bar + 2} rounded-sm ${bar <= config.bars ? config.color : 'bg-gray-200'}`}
          style={{ height: `${(bar + 2) * 3}px` }}
        />
      ))}
      <span className="ml-2 text-xs text-gray-500 capitalize">{level}</span>
    </div>
  );
}

function ScenarioCard({
  scenario,
  onLaunch,
  isLaunching,
}: {
  scenario: AttackScenario;
  onLaunch: (scenarioId: string) => void;
  isLaunching: boolean;
}) {
  const icons: Record<string, React.ElementType> = {
    apt_intrusion: ShieldExclamationIcon,
    ransomware_attack: BoltIcon,
    insider_threat: ExclamationTriangleIcon,
    web_app_attack: ShieldExclamationIcon,
    credential_theft: ShieldExclamationIcon,
  };

  const Icon = icons[scenario.id] || ShieldExclamationIcon;

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-red-100 rounded-lg p-3">
              <Icon className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">{scenario.name}</h3>
              <ThreatLevelIndicator level={scenario.threat_level} />
            </div>
          </div>
        </div>

        <p className="mt-4 text-sm text-gray-600">{scenario.description}</p>

        <div className="mt-4 flex items-center text-sm text-gray-500">
          <ClockIcon className="h-4 w-4 mr-1" />
          <span>~{scenario.estimated_duration_minutes} minutes</span>
        </div>

        <div className="mt-4">
          <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Objectives</h4>
          <ul className="space-y-1">
            {scenario.objectives.map((objective, index) => (
              <li key={index} className="flex items-center text-sm text-gray-600">
                <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                <span className="capitalize">{objective.replace(/_/g, ' ')}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
        <button
          onClick={() => onLaunch(scenario.id)}
          disabled={isLaunching}
          className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <BoltIcon className="h-4 w-4 mr-2" />
          {isLaunching ? 'Launching...' : 'Launch Scenario'}
        </button>
      </div>
    </div>
  );
}

function LaunchModal({
  isOpen,
  onClose,
  instances,
  onConfirm,
  isLaunching,
}: {
  isOpen: boolean;
  onClose: () => void;
  instances: Instance[];
  onConfirm: (instanceId: string) => void;
  isLaunching: boolean;
}) {
  const [selectedInstance, setSelectedInstance] = useState<string>('');

  const runningInstances = instances.filter((i) => i.status === 'running');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose} />

        <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Select Target Instance</h3>

          {runningInstances.length === 0 ? (
            <div className="text-center py-6">
              <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h4 className="mt-2 text-sm font-medium text-gray-900">No running instances</h4>
              <p className="mt-1 text-sm text-gray-500">
                You need at least one running Splunk instance to launch an attack scenario.
              </p>
              <a
                href="/instances/new"
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-splunk-green hover:bg-green-600"
              >
                Create Instance
              </a>
            </div>
          ) : (
            <>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {runningInstances.map((instance) => (
                  <label
                    key={instance.id}
                    className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedInstance === instance.id
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="instance"
                      value={instance.id}
                      checked={selectedInstance === instance.id}
                      onChange={(e) => setSelectedInstance(e.target.value)}
                      className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300"
                    />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">{instance.name}</p>
                      <p className="text-xs text-gray-500">{instance.id}</p>
                    </div>
                  </label>
                ))}
              </div>

              <div className="mt-6 flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => onConfirm(selectedInstance)}
                  disabled={!selectedInstance || isLaunching}
                  className="flex-1 inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <BoltIcon className="h-4 w-4 mr-2" />
                  {isLaunching ? 'Launching...' : 'Launch Attack'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Scenarios() {
  const navigate = useNavigate();
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const { data: scenarios = [], isLoading: loadingScenarios, error } = useQuery({
    queryKey: ['scenarios'],
    queryFn: attacksApi.listScenarios,
  });

  const { data: instances = [] } = useQuery({
    queryKey: ['instances'],
    queryFn: instancesApi.list,
  });

  const executeMutation = useMutation({
    mutationFn: ({ scenarioId, instanceId }: { scenarioId: string; instanceId: string }) =>
      attacksApi.executeScenario(scenarioId, instanceId),
    onSuccess: (campaign) => {
      setSelectedScenario(null);
      navigate(`/attacks/campaigns/${campaign.id}`);
    },
  });

  const handleLaunch = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
  };

  const handleConfirmLaunch = (instanceId: string) => {
    if (selectedScenario) {
      executeMutation.mutate({ scenarioId: selectedScenario, instanceId });
    }
  };

  if (loadingScenarios) {
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
          <span className="text-red-700">Failed to load scenarios</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Attack Scenarios</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pre-built attack scenarios based on real-world TTPs (Tactics, Techniques, and Procedures)
        </p>
      </div>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <ShieldExclamationIcon className="h-5 w-5 text-blue-500 flex-shrink-0" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">About Attack Scenarios</h3>
            <p className="mt-1 text-sm text-blue-700">
              These scenarios simulate real attack patterns mapped to the MITRE ATT&CK framework.
              Each scenario generates realistic security logs for detection engineering and SOC training.
              Scenarios are inspired by the Boss of the SOC (BOTS) dataset format.
            </p>
          </div>
        </div>
      </div>

      {/* Scenarios grid */}
      {scenarios.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <ShieldExclamationIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No scenarios available</h3>
          <p className="mt-1 text-sm text-gray-500">
            Attack scenarios are not configured yet.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {scenarios.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              onLaunch={handleLaunch}
              isLaunching={executeMutation.isPending && selectedScenario === scenario.id}
            />
          ))}
        </div>
      )}

      {/* Launch Modal */}
      <LaunchModal
        isOpen={selectedScenario !== null}
        onClose={() => setSelectedScenario(null)}
        instances={instances}
        onConfirm={handleConfirmLaunch}
        isLaunching={executeMutation.isPending}
      />

      {/* Error toast */}
      {executeMutation.isError && (
        <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
            <span className="text-red-700">Failed to launch scenario. Please try again.</span>
          </div>
        </div>
      )}
    </div>
  );
}
