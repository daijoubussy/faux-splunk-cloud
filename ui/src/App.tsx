import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import {
  ServerIcon,
  ShieldExclamationIcon,
  BeakerIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { healthApi } from './api';

// Pages
import Dashboard from './pages/Dashboard';
import Instances from './pages/Instances';
import InstanceDetail from './pages/InstanceDetail';
import CreateInstance from './pages/CreateInstance';
import Attacks from './pages/Attacks';
import ThreatActors from './pages/ThreatActors';
import Campaigns from './pages/Campaigns';
import CampaignDetail from './pages/CampaignDetail';
import Scenarios from './pages/Scenarios';
import AcsExplorer from './pages/AcsExplorer';

const navigation = [
  { name: 'Dashboard', href: '/', icon: ChartBarIcon },
  { name: 'Instances', href: '/instances', icon: ServerIcon },
  { name: 'Attacks', href: '/attacks', icon: ShieldExclamationIcon },
  { name: 'ACS Explorer', href: '/acs', icon: BeakerIcon },
];

function Sidebar() {
  const location = useLocation();

  return (
    <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
      <div className="flex min-h-0 flex-1 flex-col bg-gray-900">
        <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4">
          <div className="flex flex-shrink-0 items-center px-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-splunk-green rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span className="text-white font-semibold text-lg">Faux Splunk Cloud</span>
            </div>
          </div>
          <nav className="mt-8 flex-1 space-y-1 px-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== '/' && location.pathname.startsWith(item.href));
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    isActive
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white',
                    'group flex items-center px-3 py-2 text-sm font-medium rounded-md'
                  )}
                >
                  <item.icon
                    className={clsx(
                      isActive ? 'text-splunk-green' : 'text-gray-400 group-hover:text-gray-300',
                      'mr-3 h-5 w-5 flex-shrink-0'
                    )}
                  />
                  {item.name}
                </NavLink>
              );
            })}
          </nav>
        </div>
        <div className="flex flex-shrink-0 border-t border-gray-800 p-4">
          <ApiStatus />
        </div>
      </div>
    </div>
  );
}

function ApiStatus() {
  const { isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 10000,
  });

  return (
    <div className="flex items-center gap-2 text-sm">
      <div
        className={clsx(
          'w-2 h-2 rounded-full',
          isLoading ? 'bg-yellow-500' : isError ? 'bg-red-500' : 'bg-green-500'
        )}
      />
      <span className="text-gray-400">
        API: {isLoading ? 'Checking...' : isError ? 'Offline' : 'Online'}
      </span>
    </div>
  );
}

function MobileNav() {
  const location = useLocation();

  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 z-50">
      <nav className="flex justify-around">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href));
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={clsx(
                'flex flex-col items-center py-2 px-3 text-xs',
                isActive ? 'text-splunk-green' : 'text-gray-400'
              )}
            >
              <item.icon className="h-6 w-6" />
              <span className="mt-1">{item.name}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <MobileNav />

      <div className="lg:pl-64">
        <main className="py-6 px-4 sm:px-6 lg:px-8 pb-20 lg:pb-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/instances" element={<Instances />} />
            <Route path="/instances/new" element={<CreateInstance />} />
            <Route path="/instances/:id" element={<InstanceDetail />} />
            <Route path="/attacks" element={<Attacks />} />
            <Route path="/attacks/threat-actors" element={<ThreatActors />} />
            <Route path="/attacks/campaigns" element={<Campaigns />} />
            <Route path="/attacks/campaigns/:id" element={<CampaignDetail />} />
            <Route path="/attacks/scenarios" element={<Scenarios />} />
            <Route path="/acs" element={<AcsExplorer />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
