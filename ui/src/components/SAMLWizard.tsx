import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  CheckCircleIcon,
  ClipboardDocumentIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  CogIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import toast from 'react-hot-toast';

interface SAMLWizardProps {
  instanceId: string;
  instanceName: string;
  splunkBaseUrl: string;
  tenantId: string;
  onComplete?: () => void;
  onSkip?: () => void;
}

interface EnterpriseRole {
  description: string;
  splunk_roles?: string[];
  capabilities?: string[];
  permissions?: string[];
}

interface SAMLConfig {
  keycloak_client: {
    client_id: string;
    status: string;
  };
  idp_metadata: string;
  splunk_config: Record<string, Record<string, string>>;
  setup_instructions: Array<{
    step: string;
    title: string;
    description: string;
  }>;
}

const WIZARD_STEPS = [
  { id: 'roles', title: 'Enterprise Roles', icon: UserGroupIcon },
  { id: 'configure', title: 'Configure SAML', icon: CogIcon },
  { id: 'apply', title: 'Apply Config', icon: DocumentTextIcon },
  { id: 'complete', title: 'Complete', icon: CheckCircleIcon },
];

export function SAMLWizard({
  instanceId,
  instanceName,
  splunkBaseUrl,
  tenantId,
  onComplete,
  onSkip,
}: SAMLWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [samlConfig, setSamlConfig] = useState<SAMLConfig | null>(null);

  // Fetch enterprise roles
  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: ['saml', 'roles'],
    queryFn: async () => {
      const response = await fetch('/api/v1/auth/saml/wizard/roles');
      if (!response.ok) throw new Error('Failed to fetch roles');
      return response.json();
    },
  });

  // Setup SAML mutation
  const setupMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `/api/v1/auth/saml/wizard/splunk?tenant_id=${tenantId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            instance_id: instanceId,
            instance_name: instanceName,
            splunk_base_url: splunkBaseUrl,
          }),
        }
      );
      if (!response.ok) throw new Error('Failed to setup SAML');
      return response.json();
    },
    onSuccess: (data) => {
      setSamlConfig(data);
      setCurrentStep(2);
      toast.success('SAML configuration generated');
    },
    onError: () => {
      toast.error('Failed to generate SAML configuration');
    },
  });

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <RolesStep
            roles={rolesData}
            isLoading={rolesLoading}
            onNext={() => setCurrentStep(1)}
            onSkip={onSkip}
          />
        );
      case 1:
        return (
          <ConfigureStep
            instanceName={instanceName}
            onConfigure={() => setupMutation.mutate()}
            isConfiguring={setupMutation.isPending}
            onBack={() => setCurrentStep(0)}
          />
        );
      case 2:
        return (
          <ApplyStep
            config={samlConfig}
            onCopy={copyToClipboard}
            onNext={() => setCurrentStep(3)}
            onBack={() => setCurrentStep(1)}
          />
        );
      case 3:
        return (
          <CompleteStep
            config={samlConfig}
            onComplete={onComplete}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-4xl mx-auto">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <ShieldCheckIcon className="h-8 w-8 text-splunk-green" />
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              SAML Authentication Setup
            </h2>
            <p className="text-sm text-gray-500">
              Configure enterprise authentication for {instanceName}
            </p>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <nav className="flex justify-between">
          {WIZARD_STEPS.map((step, index) => (
            <div
              key={step.id}
              className={clsx(
                'flex items-center',
                index < WIZARD_STEPS.length - 1 && 'flex-1'
              )}
            >
              <div className="flex items-center">
                <div
                  className={clsx(
                    'flex items-center justify-center w-10 h-10 rounded-full border-2',
                    index < currentStep
                      ? 'bg-splunk-green border-splunk-green'
                      : index === currentStep
                      ? 'border-splunk-green bg-white'
                      : 'border-gray-300 bg-white'
                  )}
                >
                  {index < currentStep ? (
                    <CheckCircleIcon className="h-6 w-6 text-white" />
                  ) : (
                    <step.icon
                      className={clsx(
                        'h-5 w-5',
                        index === currentStep ? 'text-splunk-green' : 'text-gray-400'
                      )}
                    />
                  )}
                </div>
                <span
                  className={clsx(
                    'ml-2 text-sm font-medium',
                    index <= currentStep ? 'text-gray-900' : 'text-gray-500'
                  )}
                >
                  {step.title}
                </span>
              </div>
              {index < WIZARD_STEPS.length - 1 && (
                <div
                  className={clsx(
                    'flex-1 h-0.5 mx-4',
                    index < currentStep ? 'bg-splunk-green' : 'bg-gray-300'
                  )}
                />
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Step Content */}
      <div className="p-6">{renderStepContent()}</div>
    </div>
  );
}

// Step Components

function RolesStep({
  roles,
  isLoading,
  onNext,
  onSkip,
}: {
  roles?: { splunk_roles: Record<string, EnterpriseRole>; platform_roles: Record<string, EnterpriseRole> };
  isLoading: boolean;
  onNext: () => void;
  onSkip?: () => void;
}) {
  if (isLoading) {
    return <div className="animate-pulse h-64 bg-gray-100 rounded-lg" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Enterprise Role Definitions
        </h3>
        <p className="text-sm text-gray-600">
          These roles will be available for SAML authentication. Users assigned these
          roles in Keycloak will receive the corresponding Splunk capabilities.
        </p>
      </div>

      {/* Splunk Roles */}
      <div>
        <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
          <UserGroupIcon className="h-5 w-5" />
          Splunk Instance Roles
        </h4>
        <div className="grid gap-3 md:grid-cols-2">
          {roles?.splunk_roles &&
            Object.entries(roles.splunk_roles).map(([name, role]) => (
              <div
                key={name}
                className="border border-gray-200 rounded-lg p-4 hover:border-splunk-green transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h5 className="font-medium text-gray-900">{name}</h5>
                    <p className="text-sm text-gray-500 mt-1">{role.description}</p>
                  </div>
                </div>
                {role.splunk_roles && role.splunk_roles.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs text-gray-500">Maps to Splunk roles: </span>
                    <span className="text-xs font-mono text-gray-700">
                      {role.splunk_roles.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            ))}
        </div>
      </div>

      {/* Platform Roles */}
      <div>
        <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
          <ShieldCheckIcon className="h-5 w-5" />
          Platform Roles
        </h4>
        <div className="grid gap-3 md:grid-cols-2">
          {roles?.platform_roles &&
            Object.entries(roles.platform_roles).map(([name, role]) => (
              <div
                key={name}
                className="border border-gray-200 rounded-lg p-4 hover:border-splunk-green transition-colors"
              >
                <h5 className="font-medium text-gray-900">{name}</h5>
                <p className="text-sm text-gray-500 mt-1">{role.description}</p>
              </div>
            ))}
        </div>
      </div>

      <div className="flex justify-between pt-4 border-t border-gray-200">
        {onSkip && (
          <button
            onClick={onSkip}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
          >
            Skip SAML Setup
          </button>
        )}
        <button
          onClick={onNext}
          className="ml-auto px-6 py-2 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-splunk-green/90"
        >
          Continue to Configuration
        </button>
      </div>
    </div>
  );
}

function ConfigureStep({
  instanceName,
  onConfigure,
  isConfiguring,
  onBack,
}: {
  instanceName: string;
  onConfigure: () => void;
  isConfiguring: boolean;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Generate SAML Configuration
        </h3>
        <p className="text-sm text-gray-600">
          This will create a SAML client in Keycloak and generate the configuration
          needed for your Splunk instance.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800 mb-2">What happens next:</h4>
        <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
          <li>A SAML client will be created in your tenant's Keycloak realm</li>
          <li>Protocol mappers will be configured for Splunk attributes</li>
          <li>Role mappings will be set up based on the enterprise roles</li>
          <li>Configuration files will be generated for your Splunk instance</li>
        </ul>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <CogIcon className="h-8 w-8 text-gray-400" />
          <div>
            <p className="font-medium text-gray-900">{instanceName}</p>
            <p className="text-sm text-gray-500">SAML Service Provider</p>
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4 border-t border-gray-200">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
        >
          Back
        </button>
        <button
          onClick={onConfigure}
          disabled={isConfiguring}
          className="px-6 py-2 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-splunk-green/90 disabled:opacity-50"
        >
          {isConfiguring ? 'Generating...' : 'Generate Configuration'}
        </button>
      </div>
    </div>
  );
}

function ApplyStep({
  config,
  onCopy,
  onNext,
  onBack,
}: {
  config: SAMLConfig | null;
  onCopy: (text: string, label: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'config' | 'metadata' | 'instructions'>('config');

  if (!config) {
    return <div>No configuration available</div>;
  }

  // Format config for display
  const authConf = config.splunk_config.authentication || {};
  const samlConf = config.splunk_config.keycloak_saml || {};
  const roleMap = config.splunk_config.roleMap_keycloak_saml || {};

  const configText = `# authentication.conf

[authentication]
${Object.entries(authConf).map(([k, v]) => `${k} = ${v}`).join('\n')}

[keycloak_saml]
${Object.entries(samlConf).map(([k, v]) => `${k} = ${v}`).join('\n')}

[roleMap_keycloak_saml]
${Object.entries(roleMap).map(([k, v]) => `${k} = ${v}`).join('\n')}`;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Apply Configuration
        </h3>
        <p className="text-sm text-gray-600">
          Review and apply the generated SAML configuration to your Splunk instance.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'config', label: 'authentication.conf' },
            { id: 'metadata', label: 'IdP Metadata' },
            { id: 'instructions', label: 'Setup Steps' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={clsx(
                'py-2 px-1 border-b-2 font-medium text-sm',
                activeTab === tab.id
                  ? 'border-splunk-green text-splunk-green'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'config' && (
        <div className="relative">
          <button
            onClick={() => onCopy(configText, 'Configuration')}
            className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-600"
            title="Copy to clipboard"
          >
            <ClipboardDocumentIcon className="h-5 w-5" />
          </button>
          <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm">
            {configText}
          </pre>
          <p className="mt-2 text-sm text-gray-500">
            Copy this to <code>$SPLUNK_HOME/etc/system/local/authentication.conf</code>
          </p>
        </div>
      )}

      {activeTab === 'metadata' && (
        <div className="relative">
          <button
            onClick={() => onCopy(config.idp_metadata, 'IdP Metadata')}
            className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-600"
            title="Copy to clipboard"
          >
            <ClipboardDocumentIcon className="h-5 w-5" />
          </button>
          <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm max-h-64">
            {config.idp_metadata}
          </pre>
          <p className="mt-2 text-sm text-gray-500">
            Import this into Splunk or extract the certificate for authentication.conf
          </p>
        </div>
      )}

      {activeTab === 'instructions' && (
        <div className="space-y-4">
          {config.setup_instructions.map((instruction) => (
            <div key={instruction.step} className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-splunk-green text-white rounded-full flex items-center justify-center font-medium">
                {instruction.step}
              </div>
              <div>
                <h4 className="font-medium text-gray-900">{instruction.title}</h4>
                <p className="text-sm text-gray-600">{instruction.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between pt-4 border-t border-gray-200">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="px-6 py-2 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-splunk-green/90"
        >
          Continue
        </button>
      </div>
    </div>
  );
}

function CompleteStep({
  config,
  onComplete,
}: {
  config: SAMLConfig | null;
  onComplete?: () => void;
}) {
  return (
    <div className="text-center py-8">
      <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
        <CheckCircleIcon className="h-10 w-10 text-green-600" />
      </div>
      <h3 className="text-xl font-medium text-gray-900 mb-2">
        SAML Configuration Complete!
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        The SAML client has been created in Keycloak. Follow the setup instructions
        to complete the integration with your Splunk instance.
      </p>

      {config && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-left max-w-md mx-auto mb-6">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Client ID:</dt>
              <dd className="font-mono text-gray-900">{config.keycloak_client.client_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Status:</dt>
              <dd className="text-green-600 font-medium">
                {config.keycloak_client.status === 'created' ? 'Created' : 'Ready'}
              </dd>
            </div>
          </dl>
        </div>
      )}

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-left max-w-md mx-auto mb-6">
        <p className="text-sm text-yellow-800">
          <strong>Important:</strong> Users must be assigned roles in Keycloak to
          access Splunk. Go to Keycloak Admin Console → Users → Role Mappings.
        </p>
      </div>

      {onComplete && (
        <button
          onClick={onComplete}
          className="px-8 py-3 text-sm font-medium text-white bg-splunk-green rounded-md hover:bg-splunk-green/90"
        >
          Done
        </button>
      )}
    </div>
  );
}

export default SAMLWizard;
