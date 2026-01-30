import { Fragment } from 'react';
import { Menu, Transition } from '@headlessui/react';
import {
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { useSAML } from './SAMLProvider';

export function UserMenu() {
  const { user, isAuthenticated, isLoading, login, logout } = useSAML();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="h-8 w-8 rounded-full bg-gray-700 animate-pulse" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <button
        onClick={() => login()}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded-md"
      >
        <ArrowRightOnRectangleIcon className="h-5 w-5" />
        <span>Sign In</span>
      </button>
    );
  }

  return (
    <Menu as="div" className="relative">
      <Menu.Button className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-gray-700">
        <UserCircleIcon className="h-8 w-8 text-gray-400" />
        <div className="text-left hidden sm:block">
          <div className="text-sm font-medium text-white truncate max-w-[120px]">
            {user?.name || user?.email || user?.user_id}
          </div>
          {user?.email && (
            <div className="text-xs text-gray-400 truncate max-w-[120px]">
              {user.email}
            </div>
          )}
        </div>
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 bottom-full mb-2 w-56 origin-bottom-right rounded-md bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="py-1">
            <div className="px-4 py-2 border-b border-gray-700">
              <p className="text-sm font-medium text-white">{user?.name || user?.user_id}</p>
              <p className="text-xs text-gray-400 truncate">{user?.email}</p>
              {user?.tenant_id && (
                <p className="text-xs text-gray-500 mt-1">Tenant: {user.tenant_id}</p>
              )}
            </div>

            {user?.roles && user.roles.length > 0 && (
              <div className="px-4 py-2 border-b border-gray-700">
                <p className="text-xs text-gray-500 mb-1">Roles</p>
                <div className="flex flex-wrap gap-1">
                  {user.roles.map((role) => (
                    <span
                      key={role}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-300"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <Menu.Item>
              {({ active }) => (
                <a
                  href="/settings"
                  className={clsx(
                    active ? 'bg-gray-700 text-white' : 'text-gray-300',
                    'flex items-center gap-2 px-4 py-2 text-sm'
                  )}
                >
                  <Cog6ToothIcon className="h-5 w-5" />
                  Settings
                </a>
              )}
            </Menu.Item>

            <Menu.Item>
              {({ active }) => (
                <button
                  onClick={() => logout()}
                  className={clsx(
                    active ? 'bg-gray-700 text-white' : 'text-gray-300',
                    'flex items-center gap-2 px-4 py-2 text-sm w-full text-left'
                  )}
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  Sign Out
                </button>
              )}
            </Menu.Item>
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  );
}

export default UserMenu;
